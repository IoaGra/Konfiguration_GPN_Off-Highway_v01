"""
pdf_export.py  (V6)
===================
Erzeugt das Ergebnis-PDF (Phase 7): Empfehlung, Nutzwerte, Gewichtung,
Normwert-Tabelle mit Ziel-/Grenzwerten, dokumentierte Formeln, Datenherkunft
und die textliche Zusammenfassung des Assistenten.
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


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="TitelGross", parent=s["Title"],
                         textColor=BLAU, fontSize=20, spaceAfter=6))
    s.add(ParagraphStyle(name="Unterzeile", parent=s["Normal"],
                         textColor=colors.HexColor("#555555"), fontSize=10,
                         spaceAfter=14))
    s.add(ParagraphStyle(name="H2", parent=s["Heading2"],
                         textColor=BLAU, fontSize=13, spaceBefore=12, spaceAfter=6))
    s.add(ParagraphStyle(name="Fliess", parent=s["Normal"],
                         fontSize=10, leading=14, spaceAfter=6))
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


def _markdown_zu_absaetzen(text, stil, story):
    """Sehr einfache Markdown-Behandlung fuer die Bot-Zusammenfassung."""
    for absatz in text.split("\n"):
        absatz = absatz.strip()
        if not absatz:
            continue
        # Markdown-Tabellenzeilen ueberspringen (Tabellen stehen separat im PDF)
        if absatz.startswith("|"):
            continue
        absatz = absatz.replace("**", "").replace("###", "").replace("##", "")
        absatz = re.sub(r"^#+\s*", "", absatz)
        story.append(Paragraph(absatz, stil))


def erstelle_ergebnis_pdf(ergebnis: dict, zusammenfassung: str,
                          szenario_typ: str, optionen: list,
                          kpis: dict, aktive: list) -> bytes:
    """Baut das vollstaendige Ergebnis-PDF und gibt die Bytes zurueck."""
    puffer = io.BytesIO()
    doc = SimpleDocTemplate(puffer, pagesize=A4,
                            topMargin=1.8*cm, bottomMargin=1.8*cm,
                            leftMargin=1.8*cm, rightMargin=1.8*cm)
    s = _styles()
    story = []

    # Kopf
    story.append(Paragraph("Entscheidungsempfehlung", s["TitelGross"]))
    story.append(Paragraph(
        f"Konfiguration globaler Produktionsnetzwerke &nbsp;|&nbsp; "
        f"Szenario-Typ: {szenario_typ} &nbsp;|&nbsp; "
        f"Optionen: {', '.join(optionen)} &nbsp;|&nbsp; "
        f"{datetime.now():%d.%m.%Y %H:%M}", s["Unterzeile"]))

    # Empfehlung + Nutzwerte
    story.append(Paragraph("Empfehlung", s["H2"]))
    story.append(Paragraph(
        f"<b>{ergebnis['empfehlung']}</b> erzielt den höchsten Nutzwert auf "
        "Basis der gewählten Gewichtung.", s["Fliess"]))

    story.append(Paragraph("Nutzwerte und Rangfolge", s["H2"]))
    daten = [["Rang", "Option", "Nutzwert (0–100)"]]
    for o in sorted(ergebnis["nutzwerte"], key=ergebnis["nutzwerte"].get,
                    reverse=True):
        daten.append([str(ergebnis["raenge"][o]), o,
                      f"{ergebnis['nutzwerte'][o]:.2f}"])
    story.append(_tabelle(daten, [1.6*cm, 9*cm, 4*cm]))

    # Gewichtung
    story.append(Paragraph("Gewichtung der Leistungsdimensionen", s["H2"]))
    daten = [["Leistungsdimension", "Gewicht"]]
    for d, g in ergebnis["gewichte"].items():
        daten.append([d, f"{g*100:.0f} %"])
    story.append(_tabelle(daten, [10.6*cm, 4*cm], GRAU))

    # Dimensions-Scores
    story.append(Paragraph("Dimensions-Scores (Mittelwert der Normwerte)", s["H2"]))
    daten = [["Leistungsdimension"] + optionen]
    dims = list(ergebnis["gewichte"].keys())
    for d in dims:
        zeile = [d]
        for o in optionen:
            wert = ergebnis["dim_scores"].get(o, {}).get(d)
            zeile.append(f"{wert:.2f}" if wert is not None else "—")
        daten.append(zeile)
    breite_rest = 14.6 - 6.0
    story.append(_tabelle(daten, [6*cm] + [breite_rest/len(optionen)*cm]*len(optionen)))

    # Formeln
    story.append(Paragraph("Dokumentation der Berechnung", s["H2"]))
    story.append(Paragraph(
        "Normierung (Ziel-/Grenzwert-Verfahren, gedeckelt auf 0–100): "
        "<b>Normwert = (Istwert − Grenzwert) / (Zielwert − Grenzwert) × 100</b>. "
        "Die Richtung (höher/niedriger ist besser) ergibt sich automatisch aus "
        "der Lage von Ziel- zu Grenzwert.", s["Fliess"]))
    story.append(Paragraph(
        "Dimensions-Score = Mittelwert der Normwerte der aktiven Kennzahlen "
        "einer Dimension (Kennzahlen gleichgewichtet). "
        "<b>Nutzwert = Σ (Gewicht der Dimension × Dimensions-Score)</b>, "
        "Gewichte auf Summe 1 normiert. "
        "OEE = Anlagenverfügbarkeit × Anlageneffizienz × Qualitätsgrad. "
        "Alle Berechnungen wurden deterministisch im Anwendungscode ausgeführt.",
        s["Fliess"]))

    # Normwert-Tabelle inkl. Ziel/Grenz + Herkunft
    story.append(PageBreak())
    story.append(Paragraph("Normwerte je Kennzahl (mit Ziel-/Grenzwerten)", s["H2"]))
    kopf = ["Kennzahl", "Ziel", "Grenze"] + [f"{o}" for o in optionen]
    daten = [kopf]
    for k in aktive:
        zeile = [f"{k}", f"{kpis[k]['zielwert']:g}", f"{kpis[k]['grenzwert']:g}"]
        for o in optionen:
            nw = ergebnis["normwerte"].get(o, {}).get(k)
            ist = ergebnis.get("rohwerte", {}).get(o, {}).get(k)
            herk = ergebnis.get("herkunft", {}).get(o, {}).get(k, "")
            kurz = {"system": "S", "nutzer": "N"}.get(herk, "")
            if nw is not None and ist is not None:
                zeile.append(f"{ist:g} → {nw:.1f} ({kurz})")
            else:
                zeile.append("—")
        daten.append(zeile)
    breite_rest = 14.6 - 4.4 - 1.2 - 1.2
    story.append(_tabelle(daten,
                          [4.4*cm, 1.2*cm, 1.2*cm] +
                          [breite_rest/len(optionen)*cm]*len(optionen)))
    story.append(Paragraph(
        "Lesart je Zelle: Istwert → Normwert (Herkunft: S = aus System, "
        "N = Nutzereingabe).", s["Klein"]))

    # Textliche Zusammenfassung des Assistenten
    story.append(Paragraph("Zusammenfassung", s["H2"]))
    _markdown_zu_absaetzen(zusammenfassung, s["Fliess"], story)

    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "<i>Dieses Dokument wurde automatisch erstellt. Die Nutzwerte sind "
        "auf Basis der dokumentierten Formeln deterministisch berechnet.</i>",
        s["Klein"]))

    doc.build(story)
    puffer.seek(0)
    return puffer.getvalue()
