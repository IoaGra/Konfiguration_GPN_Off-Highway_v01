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
from xml.sax.saxutils import escape

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
SEITENBREITE_CM = 18.2


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
                         fontSize=9.5, leading=13, spaceBefore=4,
                         spaceAfter=6, leftIndent=6, fontName="Helvetica"))
    s.add(ParagraphStyle(name="Stichpunkt", parent=s["Normal"],
                         fontSize=10, leading=14, leftIndent=14,
                         bulletIndent=4, spaceAfter=3))
    s.add(ParagraphStyle(name="Klein", parent=s["Normal"],
                         fontSize=8.5, leading=12,
                         textColor=colors.HexColor("#555555")))
    s.add(ParagraphStyle(name="TabellenKopf", parent=s["Normal"],
                         fontName="Helvetica-Bold", fontSize=8.2, leading=10,
                         textColor=colors.white, alignment=1))
    s.add(ParagraphStyle(name="TabellenZelle", parent=s["Normal"],
                         fontSize=8.2, leading=10, wordWrap="CJK"))
    return s


def _html(value) -> str:
    if value is None:
        return ""
    txt = str(value).replace("\n", "<br/>")
    # Einfache Formel-Tags bleiben erhalten; normale Tabellenwerte werden escaped.
    return escape(txt)


def _tabelle(daten, breiten, s, kopf_farbe=BLAU):
    """Lesbare Tabelle mit automatischen Zeilenumbrüchen."""
    vorbereitete = []
    for r, zeile in enumerate(daten):
        stil = s["TabellenKopf"] if r == 0 else s["TabellenZelle"]
        vorbereitete.append([Paragraph(_html(zelle), stil) for zelle in zeile])

    t = Table(vorbereitete, colWidths=breiten, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), kopf_farbe),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HELL]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _formelbox(formel_html, s):
    t = Table([[Paragraph(formel_html, s["Formel"])]],
              colWidths=[SEITENBREITE_CM * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FORMELBG),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2E0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
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


def _entscheidungserlaeuterung(ergebnis: dict, optionen: list) -> str:
    """Deterministische Kurzerläuterung für die PDF, damit die Begründung
    auch dann aussagekräftig ist, wenn die LLM-Zusammenfassung knapp ausfällt.
    """
    nutzwerte = ergebnis.get("nutzwerte", {})
    if not nutzwerte or len(optionen) < 2:
        return "Die Entscheidung ergibt sich aus dem höchsten berechneten Nutzwert."

    sortiert = sorted(nutzwerte, key=nutzwerte.get, reverse=True)
    best = sortiert[0]
    vergleich = sortiert[1] if len(sortiert) > 1 else None
    if not vergleich:
        return f"{best} weist den höchsten Nutzwert auf."

    diff = nutzwerte[best] - nutzwerte[vergleich]
    text = (f"Die Empfehlung zugunsten von {best} ergibt sich aus dem höheren "
            f"Gesamtnutzwert. {best} erreicht {nutzwerte[best]:.2f} Punkte, "
            f"während {vergleich} {nutzwerte[vergleich]:.2f} Punkte erzielt. "
            f"Der Abstand beträgt damit {diff:.2f} Punkte. ")

    dim_best = ergebnis.get("dim_scores", {}).get(best, {})
    dim_vergleich = ergebnis.get("dim_scores", {}).get(vergleich, {})
    vorteile = []
    for d, wert in dim_best.items():
        if d in dim_vergleich:
            vorteile.append((wert - dim_vergleich[d], d, wert, dim_vergleich[d]))
    vorteile.sort(reverse=True)
    top = [v for v in vorteile if v[0] > 0][:3]
    if top:
        text += "Besonders deutlich zeigt sich der Vorteil in "
        teile = [f"{d} ({best}: {wb:.2f}; {vergleich}: {wv:.2f})"
                 for _, d, wb, wv in top]
        text += ", ".join(teile) + ". "
    return text


def _sichere_weitere_betrachtung(weitere: list[str], szenario_typ: str) -> list[str]:
    punkte = list(weitere)
    if "Verlagerung" in (szenario_typ or ""):
        zusatz = (
            "Eine Produktionsverlagerung betrifft nicht nur den Zielstandort, "
            "sondern auch den Ursprungsstandort. Auswirkungen auf dessen "
            "Auslastung, Fixkostendeckung, Personal, Know-how und verbleibende "
            "Baureihen sollten ergänzend bewertet werden."
        )
        if not any("Ursprungsstandort" in p for p in punkte):
            punkte.insert(0, zusatz)
    if not punkte:
        punkte = [
            "Einmalige Umstellungskosten, Anlaufverluste und Qualifizierungsaufwände sind nicht vollständig im Nutzwert abgebildet.",
            "Qualitative Risiken, rechtliche Rahmenbedingungen und lieferkettenbezogene Abhängigkeiten sollten ergänzend geprüft werden.",
        ]
    return punkte


def erstelle_ergebnis_pdf(ergebnis: dict, bot_text: str,
                          szenario_typ: str, optionen: list,
                          kpis: dict, aktive: list,
                          robustheit: dict | None = None) -> bytes:
    puffer = io.BytesIO()
    doc = SimpleDocTemplate(puffer, pagesize=A4,
                            topMargin=1.4*cm, bottomMargin=1.4*cm,
                            leftMargin=1.4*cm, rightMargin=1.4*cm)
    s = _styles()
    story = []
    breite = SEITENBREITE_CM

    # ---------------- Kopf ----------------
    story.append(Paragraph("Entscheidungsempfehlung", s["TitelGross"]))
    story.append(Paragraph(
        f"Konfiguration globaler Produktionsnetzwerke &nbsp;|&nbsp; "
        f"{datetime.now():%d.%m.%Y %H:%M}", s["Unterzeile"]))
    story.append(Paragraph(
        f"Empfehlung: <b>{escape(str(ergebnis['empfehlung']))}</b> "
        f"(höchster Nutzwert {ergebnis['nutzwerte'][ergebnis['empfehlung']]:.2f} von 100)",
        s["Fliess"]))

    # ---------------- Phase 1 ----------------
    story.append(Paragraph("Phase 1 — Auswahl des Szenarios", s["PhasenTitel"]))
    story.append(_tabelle(
        [["Szenario-Typ", "Verglichene Optionen"], [szenario_typ, ", ".join(optionen)]],
        [4.2*cm, (breite-4.2)*cm], s))

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
    story.append(_tabelle(daten, [13.2*cm, (breite-13.2)*cm], s, GRAU))

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
    story.append(_tabelle(daten, [4.0*cm, 6.5*cm, 2.0*cm, 2.8*cm, 2.9*cm], s))

    story.append(Spacer(1, 8))
    try:
        from formeln import formel_beispiele_fuer_ui
        beispiele = formel_beispiele_fuer_ui()
        if beispiele:
            story.append(Paragraph("Formeln und benötigte Eingaben:", s["Fliess"]))
            daten = [["Kennzahl", "Option", "Benötigte Nutzereingabe", "Formel", "Systemseitige Rechengrößen"]]
            for b in beispiele:
                daten.append([
                    b.get("Kennzahl", ""), b.get("Option", ""), b.get("Benötigte Nutzereingabe", ""),
                    b.get("Formel", ""), b.get("Systemseitige Rechengrößen", ""),
                ])
            story.append(_tabelle(daten, [3.2*cm, 2.1*cm, 4.9*cm, 4.5*cm, 3.5*cm], s, GRAU))
    except ImportError:
        pass

    story.append(Spacer(1, 8))
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
    rest = breite - 5.7 - 1.8
    story.append(_tabelle(daten, [5.7*cm, 1.8*cm] + [rest/len(optionen)*cm]*len(optionen), s))

    # ---------------- Phase 4 ----------------
    story.append(PageBreak())
    story.append(Paragraph("Phase 4 — Berechnung der Scores", s["PhasenTitel"]))
    story.append(Paragraph(
        "Die Rohwerte wurden ziel- und grenzwertbasiert auf eine Skala von 0 bis 100 "
        "normalisiert. Die Wirkungsrichtung wird über die Lage von Ziel- und Grenzwert "
        "berücksichtigt: Liegt der Zielwert über dem Grenzwert, sind höhere Istwerte "
        "besser; liegt der Zielwert unter dem Grenzwert, sind niedrigere Istwerte besser. "
        "Werte außerhalb des Ziel-Grenz-Korridors werden auf 0 bzw. 100 gedeckelt.",
        s["Fliess"]))
    story.append(_formelbox(
        "Allgemein: Normwert = (Istwert &minus; Grenzwert) / "
        "(Zielwert &minus; Grenzwert) &times; 100<br/>"
        "Für Zielwert &gt; Grenzwert: höhere Werte führen zu höheren Normwerten.<br/>"
        "Für Zielwert &lt; Grenzwert: niedrigere Werte führen zu höheren Normwerten, "
        "da Zähler und Nenner entsprechend negativ bzw. kleiner werden.", s))

    kopf = ["Kennzahl"] + list(optionen)
    daten = [kopf]
    for k in aktive:
        zeile = [k]
        for o in optionen:
            nw = ergebnis["normwerte"].get(o, {}).get(k)
            zeile.append(f"{nw:.1f}" if nw is not None else "—")
        daten.append(zeile)
    rest = breite - 7.0
    story.append(_tabelle(daten, [7.0*cm] + [rest/len(optionen)*cm]*len(optionen), s))

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
    rest = breite - 6.6
    story.append(_tabelle(daten, [6.6*cm] + [rest/len(optionen)*cm]*len(optionen), s))

    story.append(Paragraph("Gesamtnutzwert:", s["Fliess"]))
    story.append(_formelbox(
        "G<sub>s</sub> = &Sigma;<sub>l</sub> ( g<sub>l</sub> &middot; P<sub>s,l</sub> )", s))
    daten = [["Rang", "Option", "Nutzwert G_s (0–100)"]]
    for o in sorted(ergebnis["nutzwerte"], key=ergebnis["nutzwerte"].get, reverse=True):
        daten.append([str(ergebnis["raenge"][o]), o, f"{ergebnis['nutzwerte'][o]:.2f}"])
    story.append(_tabelle(daten, [2.0*cm, 10.4*cm, 5.8*cm], s))

    story.append(Paragraph("Entscheidungserläuterung:", s["Fliess"]))
    story.append(Paragraph(_entscheidungserlaeuterung(ergebnis, optionen), s["Fliess"]))

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
            [4.0*cm, (breite-4.0)*cm], s, GRAU))
    else:
        story.append(Paragraph("Robustheitsbewertung: —", s["Fliess"]))

    # ---------------- Phase 6 ----------------
    story.append(Paragraph("Phase 6 — Zusammenfassung", s["PhasenTitel"]))
    zus, weitere = _parse_stichpunkte(bot_text or "")
    weitere = _sichere_weitere_betrachtung(weitere, szenario_typ)

    story.append(Paragraph("<b>Zusammenfassung:</b>", s["Fliess"]))
    if zus:
        for p in zus:
            story.append(Paragraph(escape(p), s["Stichpunkt"], bulletText="•"))
    else:
        story.append(Paragraph(_entscheidungserlaeuterung(ergebnis, optionen), s["Stichpunkt"], bulletText="•"))

    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Was noch berücksichtigt werden sollte:</b>", s["Fliess"]))
    for p in weitere:
        story.append(Paragraph(escape(p), s["Stichpunkt"], bulletText="•"))

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "<i>Dieses Dokument wurde automatisch erstellt. Alle Bewertungen wurden "
        "nach den dokumentierten Formeln im Anwendungscode berechnet.</i>", s["Klein"]))

    doc.build(story)
    puffer.seek(0)
    return puffer.getvalue()
