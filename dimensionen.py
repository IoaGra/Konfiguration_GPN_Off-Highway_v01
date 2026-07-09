"""
dimensionen.py
===============
Erklärungen zu den fünf Leistungsdimensionen. Der Bot nutzt diese Texte nur
auf Nachfrage, damit der Dialog knapp bleibt.
"""

DIMENSION_BESCHREIBUNGEN = {
    "Effizienz": (
        "Die Leistungsdimension Effizienz beschreibt das Verhältnis zwischen "
        "erbrachter Leistung und dem dafür erforderlichen Ressourceneinsatz. "
        "Berücksichtigt werden insbesondere produktivitäts- und kostenbezogene "
        "Kennzahlen wie Kapazitätsauslastung, Fertigungskosten, "
        "Mitarbeitendenproduktivität oder strukturelle Ähnlichkeiten zwischen "
        "Baureihen und Standorten."
    ),
    "Qualität": (
        "Die Leistungsdimension Qualität beschreibt die Fähigkeit, Produkte "
        "zuverlässig entsprechend definierter Anforderungen bereitzustellen. "
        "Relevante Kennzahlen sind beispielsweise Qualitätsrate, "
        "Liefertermintreue und Reklamationsquote."
    ),
    "Zeit": (
        "Die Leistungsdimension Zeit bewertet die Geschwindigkeit der "
        "Leistungserbringung. Dazu zählen etwa Produktionsdurchlaufzeiten, "
        "Transportzeiten und Lieferzeiten eines Zulieferers."
    ),
    "Flexibilität": (
        "Die Leistungsdimension Flexibilität beschreibt die Fähigkeit eines "
        "Produktionsnetzwerks, auf veränderte Rahmenbedingungen zu reagieren. "
        "Dazu zählen beispielsweise Volumen-, Varianten- und "
        "Transportvolumenflexibilität."
    ),
    "Ökologische Nachhaltigkeit": (
        "Die Leistungsdimension ökologische Nachhaltigkeit beschreibt die "
        "Umweltwirkungen von Produktion und Transport. Berücksichtigt werden "
        "beispielsweise CO₂-Emissionen sowie der Anteil erneuerbarer Energie."
    ),
}


def dim_beschreibung(schluessel: str) -> str:
    return DIMENSION_BESCHREIBUNGEN.get(schluessel, "")
