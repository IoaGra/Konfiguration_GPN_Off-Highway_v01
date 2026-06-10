"""
pdf_export.py
=============
Erzeugt das Ergebnis-PDF (Phase 7) mit reportlab. Enthaelt: Empfehlung,
Ergebnistabelle (Nutzwerte/Raenge), verwendete Gewichtung und die textliche
Zusammenfassung des Bots. Gibt die PDF als Bytes zurueck (fuer den
Streamlit-Download-Button).
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from anzeige import dim_anzeige

BLAU = colors.HexColor("#2E5A88")


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
                         fontSize=10.5, leading=15, spaceAfter=8))
    return s


def erstelle_ergebnis_pdf(ergebnis: dict, zusammenfassung: str,
                          szenario_typ_label: str) -> bytes:
    """Baut das PDF und gibt die Bytes zurueck.

    ergebnis: dict aus rechne() mit 'nutzwerte', 'raenge', 'empfehlung', 'gewichte'
    zusammenfassung: vom Bot formulierter Text (Phase 7)
    szenario_typ_label: lesbarer Name des Szenario-Typs
    """
    puffer = io.BytesIO()
    doc = SimpleDocTemplate(puffer, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    s = _styles()
    story = []

    # Kopf
    story.append(Paragraph("Entscheidungsempfehlung", s["TitelGross"]))
    story.append(Paragraph(
        f"Konfiguration globaler Produktionsnetzwerke &nbsp;|&nbsp; "
        f"Szenario-Typ: {szenario_typ_label} &nbsp;|&nbsp; "
        f"{datetime.now():%d.%m.%Y %H:%M}", s["Unterzeile"]))

    # Empfehlung
    story.append(Paragraph("Empfehlung", s["H2"]))
    story.append(Paragraph(
        f"<b>{ergebnis['empfehlung']}</b> erzielt den hoechsten Nutzwert "
        "und wird auf Basis der gewaehlten Gewichtung empfohlen.", s["Fliess"]))

    # Ergebnistabelle
    story.append(Paragraph("Ergebnis im Ueberblick", s["H2"]))
    daten = [["Rang", "Szenario", "Nutzwert"]]
    for s_name, nw in sorted(ergebnis["nutzwerte"].items(),
                             key=lambda kv: kv[1], reverse=True):
        daten.append([str(ergebnis["raenge"][s_name]), s_name, f"{nw:.4f}"])
    tab = Table(daten, colWidths=[2*cm, 9*cm, 4*cm])
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLAU),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#EAF0F6")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tab)

    # Gewichtung
    story.append(Paragraph("Verwendete Gewichtung der Dimensionen", s["H2"]))
    gdaten = [["Dimension", "Gewicht"]]
    for d, w in ergebnis["gewichte"].items():
        gdaten.append([dim_anzeige(d), f"{w*100:.0f} %"])
    gtab = Table(gdaten, colWidths=[11*cm, 4*cm])
    gtab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#888888")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F4F4F4")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(gtab)

    # Zusammenfassung
    story.append(Paragraph("Zusammenfassung", s["H2"]))
    for absatz in zusammenfassung.split("\n"):
        absatz = absatz.strip()
        if absatz:
            # einfache Markdown-Fettung **...** -> <b>...</b>
            absatz = absatz.replace("**", "")  # fett-Marker entfernen (sauberer Druck)
            story.append(Paragraph(absatz, s["Fliess"]))

    story.append(Spacer(1, 18))
    story.append(Paragraph(
        "<i>Hinweis: Die Nutzwerte wurden deterministisch berechnet "
        "(relative Min-Max-Normalisierung, gewichtete Aggregation der "
        "Leistungsdimensionen). Dieses Dokument wurde automatisch erstellt.</i>",
        s["Unterzeile"]))

    doc.build(story)
    puffer.seek(0)
    return puffer.getvalue()
