"""Erzeugung der Ergebnis-PDF für den Entscheidungsprozess."""

from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Dict, List, Optional
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    CondPageBreak,
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BLAU = colors.HexColor("#245EA8")
DUNKELBLAU = colors.HexColor("#173B67")
HELLBLAU = colors.HexColor("#EAF2FC")
GRAU = colors.HexColor("#5F6874")
LINIE = colors.HexColor("#C8D2E0")
FORMELBG = colors.HexColor("#F1F5FA")
SEITENBREITE_CM = 18.2


def _styles():
    stile = getSampleStyleSheet()
    stile.add(
        ParagraphStyle(
            name="TitelGross",
            parent=stile["Title"],
            textColor=DUNKELBLAU,
            fontSize=19,
            leading=23,
            spaceAfter=8,
        )
    )
    stile.add(
        ParagraphStyle(
            name="Unterzeile",
            parent=stile["Normal"],
            textColor=GRAU,
            fontSize=9.2,
            leading=12,
            spaceAfter=12,
        )
    )
    stile.add(
        ParagraphStyle(
            name="PhasenTitel",
            parent=stile["Heading2"],
            textColor=BLAU,
            fontSize=13.5,
            leading=17,
            spaceBefore=9,
            spaceAfter=7,
            keepWithNext=True,
        )
    )
    stile.add(
        ParagraphStyle(
            name="ZwischenTitel",
            parent=stile["Heading3"],
            textColor=DUNKELBLAU,
            fontSize=10.2,
            leading=13,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        )
    )
    stile.add(
        ParagraphStyle(
            name="Fliess",
            parent=stile["Normal"],
            fontSize=9.3,
            leading=13,
            spaceAfter=6,
        )
    )
    stile.add(
        ParagraphStyle(
            name="Formel",
            parent=stile["Normal"],
            fontSize=10,
            leading=14,
            alignment=1,
        )
    )
    stile.add(
        ParagraphStyle(
            name="Klein",
            parent=stile["Normal"],
            fontSize=8,
            leading=10.5,
            textColor=GRAU,
        )
    )
    stile.add(
        ParagraphStyle(
            name="TabellenKopf",
            parent=stile["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=9.5,
            textColor=colors.white,
            alignment=1,
        )
    )
    stile.add(
        ParagraphStyle(
            name="TabellenZelle",
            parent=stile["Normal"],
            fontSize=7.8,
            leading=9.8,
            wordWrap="CJK",
        )
    )
    return stile


def _html(wert) -> str:
    if wert is None:
        return ""
    return escape(str(wert)).replace("\n", "<br/>")


def _tabelle(daten, breiten, stile, kopf_farbe=BLAU, ausrichtungen=None):
    vorbereitet = []
    for zeilenindex, zeile in enumerate(daten):
        stil = stile["TabellenKopf"] if zeilenindex == 0 else stile["TabellenZelle"]
        vorbereitet.append([Paragraph(_html(zelle), stil) for zelle in zeile])

    tabelle = Table(vorbereitet, colWidths=breiten, repeatRows=1, hAlign="LEFT")
    regeln = [
        ("BACKGROUND", (0, 0), (-1, 0), kopf_farbe),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HELLBLAU]),
        ("GRID", (0, 0), (-1, -1), 0.35, LINIE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]
    if ausrichtungen:
        for spalte, ausrichtung in enumerate(ausrichtungen):
            regeln.append(("ALIGN", (spalte, 1), (spalte, -1), ausrichtung))
    tabelle.setStyle(TableStyle(regeln))
    return tabelle


def _formelbild(latex_zeilen: List[str], breite_cm: float = 16.8) -> RLImage:
    zeilen = list(latex_zeilen or [r"-"])
    hoehe_cm = 1.0 + 0.72 * len(zeilen)
    figur = Figure(
        figsize=(breite_cm / 2.54, hoehe_cm / 2.54),
        dpi=220,
        facecolor="white",
    )
    FigureCanvasAgg(figur)
    achse = figur.add_axes([0, 0, 1, 1])
    achse.axis("off")
    for index, latex in enumerate(zeilen):
        y = 1 - (index + 0.5) / len(zeilen)
        achse.text(
            0.5,
            y,
            f"${latex}$",
            ha="center",
            va="center",
            fontsize=14 if len(zeilen) == 1 else 12.5,
            color="#111111",
        )
    puffer = io.BytesIO()
    figur.savefig(
        puffer,
        format="png",
        dpi=220,
        bbox_inches="tight",
        pad_inches=0.06,
        facecolor="white",
    )
    puffer.seek(0)
    bild = RLImage(puffer, width=breite_cm * cm, height=hoehe_cm * cm)
    bild._formula_buffer = puffer
    return bild


def _formelbox_math(latex_zeilen: List[str]):
    bild = _formelbild(latex_zeilen)
    tabelle = Table([[bild]], colWidths=[SEITENBREITE_CM * cm], hAlign="LEFT")
    tabelle.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FORMELBG),
                ("BOX", (0, 0), (-1, -1), 0.7, BLAU),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tabelle


def _deutsche_zeit() -> datetime:
    return datetime.now(ZoneInfo("Europe/Berlin"))


def _bereinige_markdown(text: str) -> str:
    text = str(text or "").strip()
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^[-*•]\s+", "", text, flags=re.MULTILINE)
    return text.strip()


def _text_abschnitte(text: str) -> List[str]:
    bereinigt = _bereinige_markdown(text)
    if not bereinigt:
        return []
    return [abschnitt.strip() for abschnitt in re.split(r"\n\s*\n", bereinigt) if abschnitt.strip()]


def _normalisiere_robustheit(robustheit) -> Optional[Dict]:
    if robustheit is None:
        return None
    if isinstance(robustheit, dict):
        return {
            "bewertung": str(robustheit.get("bewertung", "Nicht angegeben")),
            "begruendung": str(robustheit.get("begruendung", "") or ""),
        }
    return {"bewertung": str(robustheit), "begruendung": ""}


def _entscheidungserlaeuterung(ergebnis: dict) -> str:
    nutzwerte = ergebnis.get("nutzwerte", {})
    if not nutzwerte:
        return "Es liegen keine berechneten Gesamtnutzwerte vor."

    sortiert = sorted(nutzwerte, key=nutzwerte.get, reverse=True)
    beste = sortiert[0]
    text = (
        f"Die rechnerische Empfehlung lautet {beste} mit "
        f"{nutzwerte[beste]:.2f} Punkten."
    )
    if len(sortiert) < 2:
        return text

    zweite = sortiert[1]
    abstand = nutzwerte[beste] - nutzwerte[zweite]
    text += (
        f" Die zweitplatzierte Alternative {zweite} erreicht "
        f"{nutzwerte[zweite]:.2f} Punkte; der Abstand beträgt {abstand:.2f} Punkte."
    )

    gewichtete_unterschiede = []
    for dimension, wert_beste in ergebnis.get("dim_scores", {}).get(beste, {}).items():
        wert_zweite = ergebnis.get("dim_scores", {}).get(zweite, {}).get(dimension)
        if wert_zweite is None:
            continue
        differenz = wert_beste - wert_zweite
        gewicht = ergebnis.get("gewichte", {}).get(dimension, 0)
        gewichtete_unterschiede.append((abs(differenz) * gewicht, differenz, dimension))
    gewichtete_unterschiede.sort(reverse=True)

    if gewichtete_unterschiede:
        punkte = []
        for _, differenz, dimension in gewichtete_unterschiede[:2]:
            if differenz > 0:
                punkte.append(f"Vorteile der Empfehlung in {dimension}")
            elif differenz < 0:
                punkte.append(f"ein Nachteil der Empfehlung in {dimension}")
        if punkte:
            text += " Ausschlaggebend sind insbesondere " + " sowie ".join(punkte) + "."
    return text


def _weitere_betrachtung(alternativen: list[dict]) -> str:
    typen = [str(alt.get("szenario_typ", "")) for alt in alternativen]
    if any("Verlagerung" in typ for typ in typen):
        return (
            "Bei einer Produktionsverlagerung sind zusätzlich die Auswirkungen "
            "auf den Ursprungsstandort zu berücksichtigen. Dazu zählen unter "
            "anderem Auslastung, Fixkosten, Personal, Wissen und verbleibende "
            "Produktionsumfänge."
        )
    return (
        "Zusätzlich zur quantitativen Bewertung sollten einmalige Kosten, "
        "qualitative Risiken und rechtliche Rahmenbedingungen geprüft werden."
    )


def _seitenfuss(canvas, dokument):
    canvas.saveState()
    canvas.setStrokeColor(LINIE)
    canvas.setLineWidth(0.4)
    canvas.line(1.4 * cm, 1.05 * cm, 19.6 * cm, 1.05 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRAU)
    canvas.drawString(
        1.4 * cm,
        0.72 * cm,
        "Entscheidungsempfehlung zur Konfiguration globaler Produktionsnetzwerke",
    )
    canvas.drawRightString(19.6 * cm, 0.72 * cm, f"Seite {dokument.page}")
    canvas.restoreState()


def _phase(story: list, titel: str, stile, mindestplatz_cm: float = 4.2):
    story.append(CondPageBreak(mindestplatz_cm * cm))
    story.append(Paragraph(titel, stile["PhasenTitel"]))


def erstelle_ergebnis_pdf(
    ergebnis: dict,
    bot_text: str,
    alternativen: list[dict],
    baureihe: str,
    kpis: dict,
    aktive_nach_alternative: dict[str, list[str]],
    robustheit: Optional[Dict] = None,
    sensitivitaetslaeufe: Optional[list] = None,
) -> bytes:
    ergebnis = ergebnis if isinstance(ergebnis, dict) else {}
    alternativen = list(alternativen or [])
    kpis = kpis if isinstance(kpis, dict) else {}
    aktive_nach_alternative = aktive_nach_alternative or {}
    robustheit = _normalisiere_robustheit(robustheit)
    sensitivitaetslaeufe = list(sensitivitaetslaeufe or [])
    bot_text = str(bot_text or "")
    optionen = [str(alt.get("name", "")) for alt in alternativen]

    puffer = io.BytesIO()
    dokument = SimpleDocTemplate(
        puffer,
        pagesize=A4,
        topMargin=1.35 * cm,
        bottomMargin=1.35 * cm,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        title="Entscheidungsempfehlung zur Konfiguration globaler Produktionsnetzwerke",
        author="Entscheidungsassistent",
    )
    stile = _styles()
    story: list = []
    breite = SEITENBREITE_CM

    story.append(
        Paragraph(
            "Entscheidungsempfehlung zur Konfiguration globaler Produktionsnetzwerke",
            stile["TitelGross"],
        )
    )
    zeit = _deutsche_zeit()
    story.append(
        Paragraph(
            f"Erstellt am {zeit:%d.%m.%Y um %H:%M Uhr} (Deutschland)",
            stile["Unterzeile"],
        )
    )
    empfehlung = ergebnis.get("empfehlung")
    empfehlungswert = ergebnis.get("nutzwerte", {}).get(empfehlung)
    if empfehlung and empfehlungswert is not None:
        story.append(
            Paragraph(
                f"Empfehlung: <b>{escape(str(empfehlung))}</b> mit "
                f"<b>{empfehlungswert:.2f}</b> von 100 Punkten.",
                stile["Fliess"],
            )
        )

    _phase(story, "Phase 1 - Konkretisierung der Entscheidungssituation", stile)
    daten = [["Alternative", "Szenariotyp", "Datengrundlage"]]
    for alt in alternativen:
        daten.append(
            [
                alt.get("name", ""),
                alt.get("szenario_typ", ""),
                alt.get("datenoption", ""),
            ]
        )
    story.append(_tabelle(daten, [4.6 * cm, 8.6 * cm, 5.0 * cm], stile))
    if baureihe:
        story.append(Spacer(1, 5))
        story.append(
            Paragraph(f"Betrachtete Baureihe: <b>{escape(baureihe)}</b>", stile["Fliess"])
        )

    _phase(story, "Phase 2 - Gewichtung der Leistungsdimensionen", stile)
    story.append(
        Paragraph(
            "Die initialen Gewichtungen bilden die Grundlage der Basis-Bewertung "
            "und werden durch die Sensitivitätsanalyse nicht überschrieben.",
            stile["Fliess"],
        )
    )
    story.append(_formelbox_math([r"\sum_{l=1}^{5} g_l = 1 \qquad 0 \leq g_l \leq 1"]))
    story.append(Spacer(1, 5))
    daten = [["Leistungsdimension", "Gewichtung"]]
    for dimension, gewicht in ergebnis.get("gewichte", {}).items():
        daten.append([dimension, f"{gewicht * 100:.0f} %"])
    story.append(_tabelle(daten, [13.0 * cm, 5.2 * cm], stile))

    _phase(story, "Phase 3 - Zusammenstellung der Datengrundlage", stile)
    story.append(
        Paragraph(
            "Die relevanten Kennzahlen wurden über die Szenario-Kennzahl-Matrix "
            "bestimmt. Fehlende Werte wurden direkt eingegeben oder aus "
            "bereitgestellten Teilwerten berechnet.",
            stile["Fliess"],
        )
    )

    aktive_gesamt = []
    for kennzahl in kpis:
        if any(kennzahl in aktive_nach_alternative.get(option, []) for option in optionen):
            aktive_gesamt.append(kennzahl)

    story.append(Paragraph("Relevante Kennzahlen", stile["ZwischenTitel"]))
    daten = [["Leistungsdimension", "Kennzahl", "Einheit", "Relevant für"]]
    for kennzahl in aktive_gesamt:
        relevant = [
            option for option in optionen
            if kennzahl in aktive_nach_alternative.get(option, [])
        ]
        daten.append(
            [
                kpis[kennzahl]["dimension"],
                kennzahl,
                kpis[kennzahl]["einheit"],
                ", ".join(relevant),
            ]
        )
    story.append(_tabelle(daten, [4.2 * cm, 5.8 * cm, 2.4 * cm, 5.8 * cm], stile))

    formeln_aktiv = set(aktive_gesamt)
    story.append(Paragraph("Eingesetzte Formeln", stile["ZwischenTitel"]))
    if "Fertigungskosten" in formeln_aktiv:
        story.append(_formelbox_math([r"K_{FK}=B_{FEK}+B_{FGK}+B_{SEK}"]))
        story.append(Spacer(1, 4))
    if "Produktionsdurchlaufzeit" in formeln_aktiv:
        story.append(_formelbox_math([r"K_{DLZ}=T_B+T_L"]))
        story.append(Spacer(1, 4))
    if "Anteil erneuerbarer Energien" in formeln_aktiv:
        story.append(_formelbox_math([r"K_{EE}=\frac{E_E}{E_G}\cdot 100"]))
        story.append(Spacer(1, 4))

    story.append(
        _tabelle(
            [
                ["Variable", "Bedeutung"],
                ["K_FK", "Fertigungskosten je Produktionseinheit"],
                ["B_FEK", "Fertigungseinzelkosten je Produktionseinheit"],
                ["B_FGK", "Fertigungsgemeinkosten je Produktionseinheit"],
                ["B_SEK", "Sondereinzelkosten je Produktionseinheit"],
                ["K_DLZ", "Produktionsdurchlaufzeit"],
                ["T_B", "Bearbeitungszeit"],
                ["T_L", "Liegezeit"],
                ["K_EE", "Anteil erneuerbarer Energien"],
                ["E_E", "Energie aus erneuerbaren Quellen"],
                ["E_G", "Gesamtenergieverbrauch"],
            ],
            [3.0 * cm, 15.2 * cm],
            stile,
            kopf_farbe=GRAU,
        )
    )

    eingabefaktoren = ergebnis.get("eingabefaktoren", {})
    faktor_labels = {
        "fertigungseinzelkosten_pro_einheit": ("Fertigungseinzelkosten", "EUR/Stk"),
        "bearbeitungszeit": ("Bearbeitungszeit", "Tage"),
        "liegezeit": ("Liegezeit", "Tage"),
        "gesamtenergieverbrauch": ("Gesamtenergieverbrauch", "kWh/Jahr"),
    }
    faktor_zeilen = [["Alternative", "Kennzahl", "Teilwert", "Wert"]]
    for option, kennzahlen_faktoren in eingabefaktoren.items():
        if not isinstance(kennzahlen_faktoren, dict):
            continue
        for kennzahl, faktoren in kennzahlen_faktoren.items():
            if not isinstance(faktoren, dict):
                continue
            for faktor, wert in faktoren.items():
                label, einheit = faktor_labels.get(faktor, (faktor, ""))
                wert_text = f"{wert:g} {einheit}" if isinstance(wert, (int, float)) else str(wert)
                faktor_zeilen.append([option, kennzahl, label, wert_text.strip()])
    if len(faktor_zeilen) > 1:
        story.append(Paragraph("Erfasste Teilwerte", stile["ZwischenTitel"]))
        story.append(_tabelle(faktor_zeilen, [3.4 * cm, 4.8 * cm, 5.8 * cm, 4.2 * cm], stile))

    story.append(Paragraph("Vollständige Datengrundlage", stile["ZwischenTitel"]))
    daten = [["Kennzahl", "Einheit"] + optionen]
    for kennzahl in aktive_gesamt:
        zeile = [kennzahl, kpis[kennzahl]["einheit"]]
        for option in optionen:
            if kennzahl not in aktive_nach_alternative.get(option, []):
                zeile.append("Nicht relevant")
                continue
            istwert = ergebnis.get("rohwerte", {}).get(option, {}).get(kennzahl)
            quelle = ergebnis.get("herkunft", {}).get(option, {}).get(kennzahl, "")
            quelle_text = {
                "system": "System",
                "nutzer_direkt": "Direkte Eingabe",
                "nutzer_berechnet": "Berechnet",
                "nutzer": "Eingabe",
            }.get(quelle, "-")
            zeile.append(f"{istwert:g} ({quelle_text})" if istwert is not None else "-")
        daten.append(zeile)
    rest = breite - 6.0 - 1.8
    story.append(
        _tabelle(
            daten,
            [6.0 * cm, 1.8 * cm] + [rest / max(len(optionen), 1) * cm] * len(optionen),
            stile,
        )
    )

    _phase(story, "Phase 4 - Mathematische Bewertung", stile, 5.0)
    story.append(Paragraph("1. Normalisierung der Kennzahlenwerte", stile["ZwischenTitel"]))
    story.append(
        Paragraph(
            "Die Istwerte werden abhängig von ihrer Wirkungsrichtung auf 0 bis "
            "100 Punkte normalisiert.",
            stile["Fliess"],
        )
    )
    story.append(
        _formelbox_math(
            [
                r"b_{s,k}=0 \quad \mathrm{wenn}\ x_{s,k}\leq x_k^G",
                r"b_{s,k}=\frac{x_{s,k}-x_k^G}{x_k^Z-x_k^G}\cdot100 \quad \mathrm{wenn}\ x_k^G<x_{s,k}<x_k^Z",
                r"b_{s,k}=100 \quad \mathrm{wenn}\ x_{s,k}\geq x_k^Z",
            ]
        )
    )
    story.append(Spacer(1, 4))
    story.append(
        _formelbox_math(
            [
                r"b_{s,k}=100 \quad \mathrm{wenn}\ x_{s,k}\leq x_k^Z",
                r"b_{s,k}=\frac{x_k^G-x_{s,k}}{x_k^G-x_k^Z}\cdot100 \quad \mathrm{wenn}\ x_k^Z<x_{s,k}<x_k^G",
                r"b_{s,k}=0 \quad \mathrm{wenn}\ x_{s,k}\geq x_k^G",
            ]
        )
    )
    story.append(Spacer(1, 5))
    daten = [["Kennzahl"] + optionen]
    for kennzahl in aktive_gesamt:
        zeile = [kennzahl]
        for option in optionen:
            wert = ergebnis.get("normwerte", {}).get(option, {}).get(kennzahl)
            zeile.append(f"{wert:.2f}" if wert is not None else "-")
        daten.append(zeile)
    rest = breite - 7.0
    story.append(_tabelle(daten, [7.0 * cm] + [rest / max(len(optionen), 1) * cm] * len(optionen), stile))

    story.append(Paragraph("2. Aggregation zu Leistungsdimensionen", stile["ZwischenTitel"]))
    story.append(
        Paragraph(
            "Die relevanten Normwerte werden innerhalb jeder Leistungsdimension "
            "arithmetisch gemittelt.",
            stile["Fliess"],
        )
    )
    story.append(_formelbox_math([r"P_{s,l}=\frac{1}{n_{s,l}^{rel}}\sum_{K_s\in K_{s,l}^{rel}}b_{s,k}"]))
    story.append(Spacer(1, 5))
    daten = [["Leistungsdimension"] + optionen]
    for dimension in ergebnis.get("gewichte", {}):
        zeile = [dimension]
        for option in optionen:
            wert = ergebnis.get("dim_scores", {}).get(option, {}).get(dimension)
            zeile.append(f"{wert:.2f}" if wert is not None else "-")
        daten.append(zeile)
    rest = breite - 7.0
    story.append(_tabelle(daten, [7.0 * cm] + [rest / max(len(optionen), 1) * cm] * len(optionen), stile))

    story.append(Paragraph("3. Berechnung der Gesamtnutzwerte", stile["ZwischenTitel"]))
    story.append(
        Paragraph(
            "Die Dimensionswerte werden mit den initialen Gewichtungen "
            "multipliziert und addiert.",
            stile["Fliess"],
        )
    )
    story.append(_formelbox_math([r"G_s=\sum_{l=1}^{5}g_l\cdot P_{s,l}"]))
    story.append(Spacer(1, 5))
    ranking = [["Rang", "Alternative", "Gesamtnutzwert"]]
    for option in sorted(ergebnis.get("nutzwerte", {}), key=ergebnis.get("nutzwerte", {}).get, reverse=True):
        ranking.append([str(ergebnis["raenge"][option]), option, f"{ergebnis['nutzwerte'][option]:.2f}"])
    story.append(_tabelle(ranking, [2.0 * cm, 10.4 * cm, 5.8 * cm], stile))

    _phase(story, "Phase 5 - Sensitivitätsanalyse", stile)
    story.append(
        Paragraph(
            f"Es wurden {len(sensitivitaetslaeufe)} alternative Gewichtung(en) "
            "neu berechnet. Die initiale Gewichtung blieb unverändert.",
            stile["Fliess"],
        )
    )
    if robustheit:
        story.append(
            _tabelle(
                [
                    ["Robustheitsbewertung", "Begründung"],
                    [
                        robustheit.get("bewertung", "Nicht angegeben"),
                        robustheit.get("begruendung", "") or "Nicht angegeben",
                    ],
                ],
                [5.0 * cm, 13.2 * cm],
                stile,
            )
        )

    _phase(story, "Phase 6 - Zusammenfassung und Ergebnis", stile, 5.0)
    story.append(Paragraph("Ranking und Empfehlung", stile["ZwischenTitel"]))
    story.append(_tabelle(ranking, [2.0 * cm, 10.4 * cm, 5.8 * cm], stile))
    if empfehlung:
        story.append(Spacer(1, 5))
        story.append(
            Paragraph(
                f"Die Handlungsempfehlung lautet <b>{escape(str(empfehlung))}</b>.",
                stile["Fliess"],
            )
        )

    story.append(Paragraph("Kurze Einordnung", stile["ZwischenTitel"]))
    story.append(Paragraph(escape(_entscheidungserlaeuterung(ergebnis)), stile["Fliess"]))
    for abschnitt in _text_abschnitte(bot_text)[:2]:
        story.append(Paragraph(escape(abschnitt), stile["Fliess"]))

    story.append(Paragraph("Weitere zu berücksichtigende Aspekte", stile["ZwischenTitel"]))
    story.append(Paragraph(escape(_weitere_betrachtung(alternativen)), stile["Fliess"]))
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "Dieses Dokument wurde automatisch erstellt. Sämtliche numerischen "
            "Bewertungen wurden deterministisch im Anwendungscode berechnet.",
            stile["Klein"],
        )
    )

    dokument.build(story, onFirstPage=_seitenfuss, onLaterPages=_seitenfuss)
    puffer.seek(0)
    return puffer.getvalue()
