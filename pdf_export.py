"""
pdf_export.py
=============
Ergebnis-PDF fuer den validierungsorientierten Ablauf.

Die PDF dokumentiert bewusst das Basis-Ergebnis aus der initialen Gewichtung.
Ergebnisse aus der Sensitivitaetsanalyse ueberschreiben dieses Basis-Ergebnis
nicht; dokumentiert wird lediglich die Robustheitsbewertung des Nutzers.
"""

import io
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BLAU = colors.HexColor("#2E5A88")
HELL = colors.HexColor("#EAF0F6")
GRAU = colors.HexColor("#888888")
FORMELBG = colors.HexColor("#F4F6FA")


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="TitelGross", parent=s["Title"],
                         textColor=BLAU, fontSize=20, spaceAfter=6))
    s.add(ParagraphStyle(name="Unterzeile", parent=s["Normal"],
                         textColor=colors.HexColor("#555555"), fontSize=10,
                         spaceAfter=14))
    s.add(ParagraphStyle(name="PhasenTitel", parent=s["Heading2"],
                         textColor=BLAU, fontSize=13, spaceBefore=14,
                         spaceAfter=6))
    s.add(ParagraphStyle(name="Fliess", parent=s["Normal"],
                         fontSize=10, leading=14, spaceAfter=6))
    s.add(ParagraphStyle(name="Formel", parent=s["Normal"],
                         fontSize=10.5, leading=15, spaceBefore=4,
                         spaceAfter=8, leftIndent=10, fontName="Helvetica"))
    s.add(ParagraphStyle(name="Stichpunkt", parent=s["Normal"],
                         fontSize=10, leading=14, leftIndent=14,
                         bulletIndent=4, spaceAfter=3))
    s.add(ParagraphStyle(name="Klein", parent=s["Normal"],
                         fontSize=8.5, leading=12,
                         textColor=colors.HexColor("#555555")))
    return s


def _tabelle(daten, breiten, kopf_farbe=BLAU):
    t = Table(daten, colWidths=breiten, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), kopf_farbe),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HELL]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _formelbox(formel_html, s):
    t = Table([[Paragraph(formel_html, s["Formel"])]], colWidths=[14.6*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FORMELBG),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2E0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _parse_stichpunkte(text):
    def block(name):
        m = re.search(name + r"\s*:?\s*\n(.*?)(?=\n[A-ZÄÖÜ ]{6,}:|\Z)",
                      text, re.DOTALL | re.IGNORECASE)
        if not m:
            return []
        punkte = []
        for zeile in m.group(1).splitlines():
            zeile = zeile.strip()
            if zeile.startswith("- ") or zeile.startswith("• "):
                punkte.append(zeile[2:].strip().replace("**", ""))
        return punkte
    return block("ZUSAMMENFASSUNG"), block("WEITERE BETRACHTUNG")


def erstelle_ergebnis_pdf(ergebnis: dict, bot_text: str,
                          szenario_typ: str, optionen: list,
                          kpis: dict, aktive: list,
                          robustheit: dict | None = None) -> bytes:
    puffer = io.BytesIO()
    doc = SimpleDocTemplate(puffer, pagesize=A4,
                            topMargin=1.8*cm, bottomMargin=1.8*cm,
                            leftMargin=1.8*cm, rightMargin=1.8*cm)
    s = _styles()
    story = []
    breite = 14.6

    # ---------------- Kopf ----------------
    story.append(Paragraph("Entscheidungsempfehlung", s["TitelGross"]))
    story.append(Paragraph(
        f"Konfiguration globaler Produktionsnetzwerke &nbsp;|&nbsp; "
        f"{datetime.now():%d.%m.%Y %H:%M}", s["Unterzeile"]))
    story.append(Paragraph(
        f"Empfehlung: <b>{ergebnis['empfehlung']}</b> "
        f"(höchster Nutzwert {ergebnis['nutzwerte'][ergebnis['empfehlung']]:.2f} von 100)",
        s["Fliess"]))

    # ---------------- Phase 1 ----------------
    story.append(Paragraph("Phase 1 — Auswahl des Szenarios", s["PhasenTitel"]))
    story.append(_tabelle(
        [["Szenario-Typ", "Verglichene Optionen"], [szenario_typ, ", ".join(optionen)]],
        [5.5*cm, 9.1*cm]))

    # ---------------- Phase 2 ----------------
    story.append(Paragraph("Phase 2 — Gewichtung der Leistungsdimensionen", s["PhasenTitel"]))
    story.append(Paragraph(
        "Die Leistungsdimensionen wurden initial gewichtet. Diese Gewichtung "
        "bildet die Grundlage des dokumentierten Basis-Ergebnisses.", s["Fliess"]))
    story.append(_formelbox(
        "&Sigma;<sub>l</sub> g<sub>l</sub> = 1 &nbsp;&nbsp; mit &nbsp;&nbsp; "
        "0 &le; g<sub>l</sub> &le; 1", s))
    daten = [["Leistungsdimension", "Gewicht g_l"]]
    for d, g in ergebnis["gewichte"].items():
        daten.append([d, f"{g*100:.0f} %"])
    story.append(_tabelle(daten, [10.6*cm, 4.0*cm], GRAU))

    # ---------------- Phase 3 ----------------
    story.append(Paragraph("Phase 3 — Abfrage der Daten", s["PhasenTitel"]))
    story.append(Paragraph(
        "Die relevanten Kennzahlen ergeben sich aus der Szenario-Kennzahl-Matrix. "
        "Vorhandene Werte stammen aus dem System; fehlende Werte wurden durch "
        "Nutzereingaben ergänzt.", s["Fliess"]))

    daten = [["Leistungsdimension", "Kennzahl", "Einheit", "Zielwert", "Grenzwert"]]
    for k in aktive:
        daten.append([kpis[k]["dimension"], k, kpis[k]["einheit"],
                      f"{kpis[k]['zielwert']:g}", f"{kpis[k]['grenzwert']:g}"])
    story.append(_tabelle(daten, [4.1*cm, 5.0*cm, 1.6*cm, 1.9*cm, 2.0*cm]))

    story.append(Spacer(1, 8))
    try:
        from formeln import formel_liste_fuer_pdf
        formeln = formel_liste_fuer_pdf()
        if formeln:
            story.append(Paragraph("Im Tool berechnete Formel-Kennzahlen:", s["Fliess"]))
            for formel in formeln:
                story.append(_formelbox(formel.replace("×", "&times;"), s))
    except ImportError:
        pass

    kopf = ["Kennzahl", "Einheit"] + list(optionen)
    daten = [kopf]
    for k in aktive:
        zeile = [k, kpis[k]["einheit"]]
        for o in optionen:
            ist = ergebnis.get("rohwerte", {}).get(o, {}).get(k)
            herk = ergebnis.get("herkunft", {}).get(o, {}).get(k, "")
            kurz = {"system": "S", "nutzer": "N"}.get(herk, "")
            zeile.append(f"{ist:g} ({kurz})" if ist is not None else "—")
        daten.append(zeile)
    rest = breite - 4.6 - 1.6
    story.append(_tabelle(daten, [4.6*cm, 1.6*cm] + [rest/len(optionen)*cm]*len(optionen)))

    # ---------------- Phase 4 ----------------
    story.append(PageBreak())
    story.append(Paragraph("Phase 4 — Berechnung der Scores", s["PhasenTitel"]))
    story.append(Paragraph(
        "Die Rohwerte wurden ziel- und grenzwertbasiert auf eine Skala von "
        "0 bis 100 normalisiert. Werte außerhalb des Ziel-Grenz-Korridors "
        "werden auf 0 bzw. 100 gedeckelt.", s["Fliess"]))
    story.append(_formelbox(
        "Normwert = (Istwert &minus; Grenzwert) / (Zielwert &minus; Grenzwert) "
        "&times; 100", s))

    kopf = ["Kennzahl"] + list(optionen)
    daten = [kopf]
    for k in aktive:
        zeile = [k]
        for o in optionen:
            nw = ergebnis["normwerte"].get(o, {}).get(k)
            zeile.append(f"{nw:.1f}" if nw is not None else "—")
        daten.append(zeile)
    rest = breite - 5.4
    story.append(_tabelle(daten, [5.4*cm] + [rest/len(optionen)*cm]*len(optionen)))

    story.append(Paragraph("Dimensions-Scores:", s["Fliess"]))
    story.append(_formelbox(
        "P<sub>s,l</sub> = (1 / n<sub>s,l</sub><super>rel</super>) &middot; "
        "&Sigma; b<sub>s,k</sub>", s))
    dims = list(ergebnis["gewichte"].keys())
    kopf = ["Leistungsdimension"] + list(optionen)
    daten = [kopf]
    for d in dims:
        zeile = [d]
        for o in optionen:
            wert = ergebnis["dim_scores"].get(o, {}).get(d)
            zeile.append(f"{wert:.2f}" if wert is not None else "—")
        daten.append(zeile)
    rest = breite - 6.0
    story.append(_tabelle(daten, [6.0*cm] + [rest/len(optionen)*cm]*len(optionen)))

    story.append(Paragraph("Gesamtnutzwert:", s["Fliess"]))
    story.append(_formelbox(
        "G<sub>s</sub> = &Sigma;<sub>l</sub> ( g<sub>l</sub> &middot; P<sub>s,l</sub> )", s))
    daten = [["Rang", "Option", "Nutzwert G_s (0–100)"]]
    for o in sorted(ergebnis["nutzwerte"], key=ergebnis["nutzwerte"].get, reverse=True):
        daten.append([str(ergebnis["raenge"][o]), o, f"{ergebnis['nutzwerte'][o]:.2f}"])
    story.append(_tabelle(daten, [1.6*cm, 9.0*cm, 4.0*cm]))

    # ---------------- Phase 5 ----------------
    story.append(Paragraph("Phase 5 — Sensitivitätsanalyse", s["PhasenTitel"]))
    story.append(Paragraph(
        "In der Sensitivitätsanalyse wurde geprüft, ob die Empfehlung bei "
        "veränderten Gewichtungen stabil bleibt. Die Nutzwerte in diesem "
        "Dokument beziehen sich weiterhin auf die initiale Gewichtung.", s["Fliess"]))
    if robustheit:
        story.append(_tabelle(
            [["Bewertung", "Begründung"],
             [robustheit.get("bewertung", "—"), robustheit.get("begruendung", "") or "—"]],
            [4.0*cm, 10.6*cm], GRAU))
    else:
        story.append(Paragraph("Robustheitsbewertung: —", s["Fliess"]))

    # ---------------- Phase 6 ----------------
    story.append(Paragraph("Phase 6 — Zusammenfassung", s["PhasenTitel"]))
    zus, weitere = _parse_stichpunkte(bot_text or "")

    story.append(Paragraph("<b>Zusammenfassung:</b>", s["Fliess"]))
    if zus:
        for p in zus:
            story.append(Paragraph(p, s["Stichpunkt"], bulletText="•"))
    else:
        story.append(Paragraph("—", s["Stichpunkt"]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Was noch berücksichtigt werden sollte:</b>", s["Fliess"]))
    if weitere:
        for p in weitere:
            story.append(Paragraph(p, s["Stichpunkt"], bulletText="•"))
    else:
        story.append(Paragraph("—", s["Stichpunkt"]))

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "<i>Dieses Dokument wurde automatisch erstellt. Alle Bewertungen wurden "
        "nach den dokumentierten Formeln im Anwendungscode berechnet.</i>", s["Klein"]))

    doc.build(story)
    puffer.seek(0)
    return puffer.getvalue()
