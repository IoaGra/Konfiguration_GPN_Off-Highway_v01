"""Erzeugt die Ergebnis-PDF für den validierungsorientierten Ablauf.

Die PDF dokumentiert das Basis-Ergebnis aus der initialen Gewichtung. Die
Sensitivitätsanalyse überschreibt dieses Ergebnis nicht, sondern ergänzt es
um die Robustheitsbewertung der nutzenden Person.
"""

import io
import re
from datetime import datetime
from typing import Dict, List, Optional
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BLAU = colors.HexColor("#245EA8")
DUNKELBLAU = colors.HexColor("#173B67")
HELLBLAU = colors.HexColor("#EAF2FC")
SEHR_HELL = colors.HexColor("#F6F8FB")
GRAU = colors.HexColor("#5F6874")
LINIE = colors.HexColor("#C8D2E0")
FORMELBG = colors.HexColor("#F1F5FA")
SEITENBREITE_CM = 18.2


def _styles():
    s = getSampleStyleSheet()
    s.add(
        ParagraphStyle(
            name="TitelGross",
            parent=s["Title"],
            textColor=DUNKELBLAU,
            fontSize=19,
            leading=23,
            spaceAfter=8,
        )
    )
    s.add(
        ParagraphStyle(
            name="Unterzeile",
            parent=s["Normal"],
            textColor=GRAU,
            fontSize=9.5,
            leading=12,
            spaceAfter=14,
        )
    )
    s.add(
        ParagraphStyle(
            name="PhasenTitel",
            parent=s["Heading2"],
            textColor=BLAU,
            fontSize=14,
            leading=17,
            spaceBefore=0,
            spaceAfter=9,
            keepWithNext=True,
        )
    )
    s.add(
        ParagraphStyle(
            name="ZwischenTitel",
            parent=s["Heading3"],
            textColor=DUNKELBLAU,
            fontSize=10.5,
            leading=13,
            spaceBefore=9,
            spaceAfter=5,
            keepWithNext=True,
        )
    )
    s.add(
        ParagraphStyle(
            name="Fliess",
            parent=s["Normal"],
            fontSize=9.6,
            leading=13.5,
            spaceAfter=7,
        )
    )
    s.add(
        ParagraphStyle(
            name="Formel",
            parent=s["Normal"],
            fontSize=10.2,
            leading=15,
            alignment=1,
            spaceAfter=0,
        )
    )
    s.add(
        ParagraphStyle(
            name="Klein",
            parent=s["Normal"],
            fontSize=8.2,
            leading=11,
            textColor=GRAU,
        )
    )
    s.add(
        ParagraphStyle(
            name="TabellenKopf",
            parent=s["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.2,
            leading=10,
            textColor=colors.white,
            alignment=1,
        )
    )
    s.add(
        ParagraphStyle(
            name="TabellenZelle",
            parent=s["Normal"],
            fontSize=8.2,
            leading=10.2,
            wordWrap="CJK",
        )
    )
    return s


def _html(value) -> str:
    if value is None:
        return ""
    return escape(str(value)).replace("\n", "<br/>")


def _tabelle(daten, breiten, s, kopf_farbe=BLAU, alignments=None):
    """Erstellt eine umbrechende, über mehrere Seiten teilbare Tabelle."""
    vorbereitet = []
    for r, zeile in enumerate(daten):
        stil = s["TabellenKopf"] if r == 0 else s["TabellenZelle"]
        vorbereitet.append([Paragraph(_html(zelle), stil) for zelle in zeile])

    t = Table(vorbereitet, colWidths=breiten, repeatRows=1, hAlign="LEFT")
    regeln = [
        ("BACKGROUND", (0, 0), (-1, 0), kopf_farbe),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HELLBLAU]),
        ("GRID", (0, 0), (-1, -1), 0.35, LINIE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if alignments:
        for spalte, ausrichtung in enumerate(alignments):
            regeln.append(("ALIGN", (spalte, 1), (spalte, -1), ausrichtung))
    t.setStyle(TableStyle(regeln))
    return t


def _formelbox(formel_html, s):
    t = Table(
        [[Paragraph(formel_html, s["Formel"])]],
        colWidths=[SEITENBREITE_CM * cm],
        hAlign="LEFT",
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), FORMELBG),
                ("BOX", (0, 0), (-1, -1), 0.7, BLAU),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


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
    return [p.strip() for p in re.split(r"\n\s*\n", bereinigt) if p.strip()]


def _entscheidungserlaeuterung(ergebnis: dict, optionen: list) -> str:
    nutzwerte = ergebnis.get("nutzwerte", {})
    if not nutzwerte:
        return "Für die Entscheidung liegen keine berechneten Nutzwerte vor."

    sortiert = sorted(nutzwerte, key=nutzwerte.get, reverse=True)
    best = sortiert[0]
    text = (
        f"Die Empfehlung lautet {best}, da diese Option mit "
        f"{nutzwerte[best]:.2f} Punkten den höchsten Gesamtnutzwert erreicht. "
    )

    if len(sortiert) >= 2:
        vergleich = sortiert[1]
        differenz = nutzwerte[best] - nutzwerte[vergleich]
        text += (
            f"Die nächstplatzierte Option {vergleich} erreicht "
            f"{nutzwerte[vergleich]:.2f} Punkte; der Abstand beträgt "
            f"{differenz:.2f} Punkte. "
        )

        dim_best = ergebnis.get("dim_scores", {}).get(best, {})
        dim_vergleich = ergebnis.get("dim_scores", {}).get(vergleich, {})
        gewichte = ergebnis.get("gewichte", {})
        vergleiche = []
        for dimension, wert_best in dim_best.items():
            if dimension not in dim_vergleich:
                continue
            wert_vergleich = dim_vergleich[dimension]
            differenz_dim = wert_best - wert_vergleich
            vergleiche.append(
                (
                    abs(differenz_dim) * gewichte.get(dimension, 0),
                    differenz_dim,
                    dimension,
                    wert_best,
                    wert_vergleich,
                    gewichte.get(dimension, 0),
                )
            )
        vergleiche.sort(reverse=True)

        if vergleiche:
            saetze = []
            for _, diff, dim, wb, wv, gewicht in vergleiche:
                if diff > 0:
                    richtung = f"liegt {best} vor {vergleich}"
                elif diff < 0:
                    richtung = f"liegt {vergleich} vor {best}"
                else:
                    richtung = "besteht Gleichstand"
                saetze.append(
                    f"In der Leistungsdimension {dim} {richtung} "
                    f"({best}: {wb:.2f}; {vergleich}: {wv:.2f}; "
                    f"Gewichtung: {gewicht * 100:.0f} Prozent)"
                )
            text += "Die Bewertung nach Leistungsdimensionen zeigt: " + "; ".join(saetze) + "."

    return text


def _weitere_betrachtung(szenario_typ: str) -> str:
    if "Verlagerung" in (szenario_typ or ""):
        return (
            "Bei einer Produktionsverlagerung sind ergänzend die Auswirkungen "
            "auf den Ursprungsstandort zu untersuchen. Dazu gehören insbesondere "
            "die verbleibende Kapazitätsauslastung, die Fixkostendeckung, "
            "personelle Auswirkungen, der Erhalt von Wissen sowie mögliche "
            "Folgen für die dort verbleibenden Baureihen. Darüber hinaus sollten "
            "einmalige Verlagerungs- und Anlaufkosten, Qualifizierungsaufwände, "
            "rechtliche Rahmenbedingungen und qualitative Risiken berücksichtigt "
            "werden."
        )
    return (
        "Zusätzlich zur quantitativen Bewertung sollten einmalige Kosten, "
        "qualitative Risiken, rechtliche Rahmenbedingungen und Auswirkungen auf "
        "weitere Elemente des Produktionsnetzwerks geprüft werden."
    )


def _seitenfuss(canvas, doc):
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
    canvas.drawRightString(19.6 * cm, 0.72 * cm, f"Seite {doc.page}")
    canvas.restoreState()


def _normalisiere_robustheit(robustheit) -> Optional[Dict]:
    """Akzeptiert aus Gründen der Abwärtskompatibilität Dict oder Text."""
    if robustheit is None:
        return None
    if isinstance(robustheit, dict):
        return {
            "bewertung": str(robustheit.get("bewertung", "Nicht angegeben")),
            "begruendung": str(robustheit.get("begruendung", "") or ""),
        }
    if isinstance(robustheit, str):
        return {"bewertung": robustheit, "begruendung": ""}
    return {"bewertung": str(robustheit), "begruendung": ""}


def erstelle_ergebnis_pdf(
    ergebnis: dict,
    bot_text: str,
    szenario_typ: str,
    baureihe: str,
    optionen: list,
    kpis: dict,
    aktive: list,
    robustheit: Optional[Dict] = None,
) -> bytes:
    ergebnis = ergebnis if isinstance(ergebnis, dict) else {}
    optionen = list(optionen or [])
    kpis = kpis if isinstance(kpis, dict) else {}
    aktive = list(aktive or [])
    robustheit = _normalisiere_robustheit(robustheit)
    szenario_typ = str(szenario_typ or "")
    baureihe = str(baureihe or "")
    bot_text = str(bot_text or "")

    puffer = io.BytesIO()
    doc = SimpleDocTemplate(
        puffer,
        pagesize=A4,
        topMargin=1.35 * cm,
        bottomMargin=1.35 * cm,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        title="Entscheidungsempfehlung zur Konfiguration globaler Produktionsnetzwerke",
        author="Entscheidungsassistent",
    )
    s = _styles()
    story = []
    breite = SEITENBREITE_CM

    # Kopf und Phase 1
    story.append(
        Paragraph(
            "Entscheidungsempfehlung zur Konfiguration globaler Produktionsnetzwerke",
            s["TitelGross"],
        )
    )
    zeit = _deutsche_zeit()
    story.append(
        Paragraph(
            f"Erstellt am {zeit:%d.%m.%Y um %H:%M Uhr} (Deutschland)",
            s["Unterzeile"],
        )
    )
    empfehlung = ergebnis.get("empfehlung", "-")
    nutzwert_empfehlung = ergebnis.get("nutzwerte", {}).get(empfehlung)
    if nutzwert_empfehlung is not None:
        story.append(
            Paragraph(
                f"Empfehlung: <b>{escape(str(empfehlung))}</b> mit einem "
                f"Gesamtnutzwert von <b>{nutzwert_empfehlung:.2f}</b> von 100 Punkten.",
                s["Fliess"],
            )
        )

    story.append(Paragraph("Phase 1 - Auswahl des Szenarios", s["PhasenTitel"]))
    story.append(
        _tabelle(
            [
                ["Merkmal", "Festlegung"],
                ["Szenario-Typ", szenario_typ],
                ["Betrachtete Baureihe", baureihe or "Nicht angegeben"],
                ["Verglichene Optionen", ", ".join(optionen)],
            ],
            [5.0 * cm, (breite - 5.0) * cm],
            s,
        )
    )

    # Phase 2
    story.append(PageBreak())
    story.append(
        Paragraph(
            "Phase 2 - Gewichtung der Leistungsdimensionen",
            s["PhasenTitel"],
        )
    )
    story.append(
        Paragraph(
            "Die fünf Leistungsdimensionen wurden durch die nutzende Person "
            "gewichtet. Die Summe der Gewichtungen beträgt 100 Prozent. Diese "
            "initiale Gewichtung bildet die Grundlage des dokumentierten "
            "Basis-Ergebnisses.",
            s["Fliess"],
        )
    )
    story.append(
        _formelbox(
            "&Sigma;<sub>l=1</sub><super>5</super> g<sub>l</sub> = 1 "
            "&nbsp;&nbsp;&nbsp; mit &nbsp;&nbsp;&nbsp; 0 &le; g<sub>l</sub> &le; 1",
            s,
        )
    )
    story.append(Spacer(1, 7))
    daten = [["Leistungsdimension", "Gewichtung"]]
    for d, g in ergebnis.get("gewichte", {}).items():
        daten.append([d, f"{g * 100:.0f} %"])
    story.append(_tabelle(daten, [13.0 * cm, 5.2 * cm], s))
    story.append(Spacer(1, 7))
    story.append(
        _tabelle(
            [
                ["Variable", "Bedeutung"],
                ["g_l", "Gewichtung der Leistungsdimension l"],
                ["l", "Index der Leistungsdimension"],
            ],
            [3.0 * cm, 15.2 * cm],
            s,
            kopf_farbe=GRAU,
        )
    )

    # Phase 3
    story.append(PageBreak())
    story.append(Paragraph("Phase 3 - Abfrage der Daten", s["PhasenTitel"]))
    story.append(
        Paragraph(
            "Die für das Szenario relevanten Kennzahlen wurden im Hintergrund "
            "über die Szenario-Kennzahl-Matrix ausgewählt. Vorhandene Werte "
            "stammen aus den Systemdaten; fehlende Werte wurden durch die "
            "nutzende Person ergänzt. Abgeleitete Kennzahlen wurden anschließend "
            "deterministisch berechnet.",
            s["Fliess"],
        )
    )

    story.append(Paragraph("Relevante Kennzahlen", s["ZwischenTitel"]))
    daten = [["Leistungsdimension", "Kennzahl", "Einheit", "Zielwert", "Grenzwert"]]
    for k in aktive:
        daten.append(
            [
                kpis[k]["dimension"],
                k,
                kpis[k]["einheit"],
                f"{kpis[k]['zielwert']:g}",
                f"{kpis[k]['grenzwert']:g}",
            ]
        )
    story.append(
        _tabelle(
            daten,
            [4.4 * cm, 5.6 * cm, 2.3 * cm, 2.9 * cm, 3.0 * cm],
            s,
        )
    )

    story.append(Paragraph("Eingesetzte Formeln", s["ZwischenTitel"]))
    if "Fertigungskosten" in aktive:
        story.append(
            _formelbox(
                "K<sub>FK</sub> = "
                "(B<sub>FEK</sub> + B<sub>FGK</sub> + B<sub>SEK</sub>) / 1000",
                s,
            )
        )
        story.append(Spacer(1, 5))
        story.append(
            _tabelle(
                [
                    ["Variable", "Bedeutung", "Einheit"],
                    ["K_FK", "Fertigungskosten je Produktionseinheit", "Tsd. EUR/Stk"],
                    ["B_FEK", "Fertigungseinzelkosten je Produktionseinheit", "EUR/Stk"],
                    ["B_FGK", "Fertigungsgemeinkosten je Produktionseinheit", "EUR/Stk"],
                    ["B_SEK", "Sondereinzelkosten je Produktionseinheit", "EUR/Stk"],
                    ["1000", "Umrechnung von EUR in Tsd. EUR", "-"],
                ],
                [2.7 * cm, 11.4 * cm, 4.1 * cm],
                s,
                kopf_farbe=GRAU,
            )
        )
        story.append(Spacer(1, 7))

    if "Anteil erneuerbarer Energien" in aktive:
        story.append(
            _formelbox(
                "K<sub>EE</sub> = (E<sub>E</sub> / E<sub>G</sub>) &times; 100",
                s,
            )
        )
        story.append(Spacer(1, 5))
        story.append(
            _tabelle(
                [
                    ["Variable", "Bedeutung", "Einheit"],
                    ["K_EE", "Anteil erneuerbarer Energien", "%"],
                    ["E_E", "Energie aus erneuerbaren Quellen", "kWh/Jahr"],
                    ["E_G", "Gesamtenergieverbrauch", "kWh/Jahr"],
                ],
                [2.7 * cm, 11.4 * cm, 4.1 * cm],
                s,
                kopf_farbe=GRAU,
            )
        )

    story.append(Paragraph("Vollständige Datengrundlage", s["ZwischenTitel"]))
    daten = [["Kennzahl", "Einheit"] + list(optionen)]
    for k in aktive:
        zeile = [k, kpis[k]["einheit"]]
        for o in optionen:
            ist = ergebnis.get("rohwerte", {}).get(o, {}).get(k)
            herk = ergebnis.get("herkunft", {}).get(o, {}).get(k, "")
            quelle = {"system": "System", "nutzer": "Eingabe"}.get(herk, "-")
            zeile.append(f"{ist:g} ({quelle})" if ist is not None else "-")
        daten.append(zeile)
    rest = breite - 6.1 - 2.0
    options_breite = rest / max(len(optionen), 1)
    story.append(
        _tabelle(
            daten,
            [6.1 * cm, 2.0 * cm] + [options_breite * cm] * len(optionen),
            s,
        )
    )

    # Phase 4
    story.append(PageBreak())
    story.append(Paragraph("Phase 4 - Berechnung der Scores", s["PhasenTitel"]))
    story.append(
        Paragraph(
            "Die Normierung unterscheidet ausdrücklich zwischen den beiden "
            "Wirkungsrichtungen. Liegt der Zielwert über dem Grenzwert, werden "
            "höhere Istwerte besser bewertet. Liegt der Zielwert unter dem "
            "Grenzwert, werden niedrigere Istwerte besser bewertet. Werte "
            "außerhalb des Ziel-Grenz-Bereichs werden auf 0 beziehungsweise "
            "100 Punkte begrenzt.",
            s["Fliess"],
        )
    )

    story.append(Paragraph("Normierung: höhere Werte sind besser", s["ZwischenTitel"]))
    story.append(
        _formelbox(
            "b<sub>s,k</sub> = 0 &nbsp; für &nbsp; x<sub>s,k</sub> &le; x<sub>k</sub><super>G</super><br/>"
            "b<sub>s,k</sub> = "
            "(x<sub>s,k</sub> - x<sub>k</sub><super>G</super>) / "
            "(x<sub>k</sub><super>Z</super> - x<sub>k</sub><super>G</super>) &times; 100 "
            "&nbsp; für &nbsp; x<sub>k</sub><super>G</super> &lt; x<sub>s,k</sub> &lt; x<sub>k</sub><super>Z</super><br/>"
            "b<sub>s,k</sub> = 100 &nbsp; für &nbsp; x<sub>s,k</sub> &ge; x<sub>k</sub><super>Z</super>",
            s,
        )
    )

    story.append(Paragraph("Normierung: niedrigere Werte sind besser", s["ZwischenTitel"]))
    story.append(
        _formelbox(
            "b<sub>s,k</sub> = 100 &nbsp; für &nbsp; x<sub>s,k</sub> &le; x<sub>k</sub><super>Z</super><br/>"
            "b<sub>s,k</sub> = "
            "(x<sub>k</sub><super>G</super> - x<sub>s,k</sub>) / "
            "(x<sub>k</sub><super>G</super> - x<sub>k</sub><super>Z</super>) &times; 100 "
            "&nbsp; für &nbsp; x<sub>k</sub><super>Z</super> &lt; x<sub>s,k</sub> &lt; x<sub>k</sub><super>G</super><br/>"
            "b<sub>s,k</sub> = 0 &nbsp; für &nbsp; x<sub>s,k</sub> &ge; x<sub>k</sub><super>G</super>",
            s,
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        _tabelle(
            [
                ["Variable", "Bedeutung"],
                ["b_s,k", "Normierter Wert der Kennzahl k für Option s"],
                ["x_s,k", "Istwert der Kennzahl k für Option s"],
                ["x_k^Z", "Zielwert der Kennzahl k"],
                ["x_k^G", "Grenzwert der Kennzahl k"],
            ],
            [3.0 * cm, 15.2 * cm],
            s,
            kopf_farbe=GRAU,
        )
    )

    story.append(Paragraph("Normwerte der Kennzahlen", s["ZwischenTitel"]))
    daten = [["Kennzahl"] + list(optionen)]
    for k in aktive:
        zeile = [k]
        for o in optionen:
            nw = ergebnis.get("normwerte", {}).get(o, {}).get(k)
            zeile.append(f"{nw:.2f}" if nw is not None else "-")
        daten.append(zeile)
    rest = breite - 7.2
    story.append(
        _tabelle(
            daten,
            [7.2 * cm] + [rest / max(len(optionen), 1) * cm] * len(optionen),
            s,
        )
    )

    story.append(Paragraph("Aggregation zu Leistungsdimensionen", s["ZwischenTitel"]))
    story.append(
        _formelbox(
            "P<sub>s,l</sub> = (1 / n<sub>s,l</sub><super>rel</super>) "
            "&times; &Sigma; b<sub>s,k</sub>",
            s,
        )
    )
    story.append(Spacer(1, 5))
    story.append(
        _tabelle(
            [
                ["Variable", "Bedeutung"],
                ["P_s,l", "Punktzahl der Leistungsdimension l für Option s"],
                ["n_s,l^rel", "Anzahl der relevanten Kennzahlen in Leistungsdimension l"],
                ["b_s,k", "Normierter Wert der relevanten Kennzahl k"],
            ],
            [3.0 * cm, 15.2 * cm],
            s,
            kopf_farbe=GRAU,
        )
    )

    daten = [["Leistungsdimension"] + list(optionen)]
    for d in ergebnis.get("gewichte", {}):
        zeile = [d]
        for o in optionen:
            wert = ergebnis.get("dim_scores", {}).get(o, {}).get(d)
            zeile.append(f"{wert:.2f}" if wert is not None else "-")
        daten.append(zeile)
    rest = breite - 7.0
    story.append(
        _tabelle(
            daten,
            [7.0 * cm] + [rest / max(len(optionen), 1) * cm] * len(optionen),
            s,
        )
    )

    story.append(Paragraph("Berechnung des Gesamtnutzwertes", s["ZwischenTitel"]))
    story.append(
        _formelbox(
            "G<sub>s</sub> = &Sigma;<sub>l=1</sub><super>5</super> "
            "g<sub>l</sub> &times; P<sub>s,l</sub>",
            s,
        )
    )
    story.append(Spacer(1, 5))
    story.append(
        _tabelle(
            [
                ["Variable", "Bedeutung"],
                ["G_s", "Gesamtnutzwert der Option s"],
                ["g_l", "Gewichtung der Leistungsdimension l"],
                ["P_s,l", "Punktzahl der Leistungsdimension l für Option s"],
            ],
            [3.0 * cm, 15.2 * cm],
            s,
            kopf_farbe=GRAU,
        )
    )

    daten = [["Rang", "Option", "Gesamtnutzwert"]]
    for o in sorted(
        ergebnis.get("nutzwerte", {}),
        key=ergebnis.get("nutzwerte", {}).get,
        reverse=True,
    ):
        daten.append(
            [
                str(ergebnis["raenge"][o]),
                o,
                f"{ergebnis['nutzwerte'][o]:.2f}",
            ]
        )
    story.append(_tabelle(daten, [2.0 * cm, 10.4 * cm, 5.8 * cm], s))

    # Phase 5
    story.append(PageBreak())
    story.append(Paragraph("Phase 5 - Sensitivitätsanalyse", s["PhasenTitel"]))
    story.append(
        Paragraph(
            "In der Sensitivitätsanalyse wurden die Gewichtungen mehrfach "
            "variiert und die Nutzwerte erneut berechnet. Die in dieser PDF "
            "dokumentierten Gewichtungen und Ergebnisse bleiben dennoch die "
            "initialen Werte aus der Basis-Bewertung.",
            s["Fliess"],
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
                s,
            )
        )
    else:
        story.append(
            Paragraph(
                "Es wurde keine Robustheitsbewertung dokumentiert.",
                s["Fliess"],
            )
        )

    # Phase 6
    story.append(PageBreak())
    story.append(Paragraph("Phase 6 - Zusammenfassung und Ergebnis", s["PhasenTitel"]))

    story.append(Paragraph("Gewichtungen der Leistungsdimensionen", s["ZwischenTitel"]))
    daten = [["Leistungsdimension", "Gewichtung"]]
    for d, g in ergebnis.get("gewichte", {}).items():
        daten.append([d, f"{g * 100:.0f} %"])
    story.append(_tabelle(daten, [13.0 * cm, 5.2 * cm], s))

    story.append(Paragraph("Finale Werte der Leistungsdimensionen", s["ZwischenTitel"]))
    daten = [["Leistungsdimension"] + list(optionen)]
    for d in ergebnis.get("gewichte", {}):
        zeile = [d]
        for o in optionen:
            wert = ergebnis.get("dim_scores", {}).get(o, {}).get(d)
            zeile.append(f"{wert:.2f}" if wert is not None else "-")
        daten.append(zeile)
    rest = breite - 7.0
    story.append(
        _tabelle(
            daten,
            [7.0 * cm] + [rest / max(len(optionen), 1) * cm] * len(optionen),
            s,
        )
    )

    story.append(Paragraph("Textliche Einordnung", s["ZwischenTitel"]))
    story.append(Paragraph(escape(_entscheidungserlaeuterung(ergebnis, optionen)), s["Fliess"]))

    bot_abschnitte = _text_abschnitte(bot_text)
    for abschnitt in bot_abschnitte:
        story.append(Paragraph(escape(abschnitt), s["Fliess"]))

    story.append(Paragraph("Weitere zu berücksichtigende Aspekte", s["ZwischenTitel"]))
    story.append(Paragraph(escape(_weitere_betrachtung(szenario_typ)), s["Fliess"]))

    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "Dieses Dokument wurde automatisch erstellt. Sämtliche numerischen "
            "Bewertungen wurden deterministisch nach den dokumentierten Formeln "
            "im Anwendungscode berechnet.",
            s["Klein"],
        )
    )

    doc.build(story, onFirstPage=_seitenfuss, onLaterPages=_seitenfuss)
    puffer.seek(0)
    return puffer.getvalue()
