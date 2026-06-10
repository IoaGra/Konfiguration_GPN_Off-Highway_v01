"""
dimensionen.py
==============
Erklaerungen zu den Leistungsdimensionen. Diese Texte zeigt der Chatbot in
Phase 2 zusaetzlich zu den Kennzahlen an, damit der Nutzer versteht, was die
jeweilige Dimension misst.

>>> HIER traegst du deine eigenen Erklaerungen ein. <<<
Die Schluessel sind die TECHNISCHEN Dimensionsnamen (ohne Umlaute), exakt wie
in der Matrix-CSV. Die Anzeige mit Umlauten uebernimmt anzeige.py.
"""

DIMENSION_BESCHREIBUNGEN = {
    "Effizienz": (
        "Effizienz beschreibt das Verhaeltnis von Output zu eingesetzten "
        "Ressourcen (Kosten, Zeit, Material). [zu ergänzen]"
    ),
    "Qualitaet": (
        "Qualitaet erfasst, wie zuverlaessig die Produktion fehlerfreie "
        "Ergebnisse und termingerechte Lieferungen erzielt. [zu ergänzen]"
    ),
    "Zeit": (
        "Zeit umfasst Durchlauf-, Wiederbeschaffungs- und Reaktionszeiten "
        "sowie die Termintreue. [zu ergänzen]"
    ),
    "Flexibilitaet": (
        "Flexibilitaet beschreibt die Faehigkeit, auf Varianten-, Mengen- "
        "und Bedarfsschwankungen zu reagieren. [zu ergänzen]"
    ),
    "Oekologische Nachhaltigkeit": (
        "Oekologische Nachhaltigkeit erfasst Umweltwirkungen wie Emissionen, "
        "Energie- und Materialeinsatz. [zu ergänzen]"
    ),
}


def dim_beschreibung(schluessel: str) -> str:
    """Beschreibung einer Dimension; faellt auf leeren Text zurueck."""
    return DIMENSION_BESCHREIBUNGEN.get(schluessel, "")
