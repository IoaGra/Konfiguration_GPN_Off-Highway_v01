"""Beschreibungstexte der fünf Leistungsdimensionen."""

DIMENSION_BESCHREIBUNGEN = {
    "Effizienz": (
        "Die Effizienz beschreibt das Verhältnis zwischen erbrachter Leistung "
        "und dem dafür erforderlichen Ressourceneinsatz. Berücksichtigt werden "
        "insbesondere produktivitäts- und kostenbezogene Kennzahlen."
    ),
    "Qualität": (
        "Die Qualität beschreibt die Fähigkeit, Produkte zuverlässig und gemäß "
        "definierter Anforderungen bereitzustellen."
    ),
    "Zeit": (
        "Die Zeit bewertet die Geschwindigkeit, mit der Produktions-, Transport- "
        "und Lieferprozesse durchgeführt werden."
    ),
    "Flexibilität": (
        "Die Flexibilität beschreibt die Fähigkeit des Produktionsnetzwerks, "
        "sich an veränderte Mengen, Varianten und Rahmenbedingungen anzupassen."
    ),
    "Ökologische Nachhaltigkeit": (
        "Die ökologische Nachhaltigkeit bewertet die Umweltwirkungen von "
        "Produktion und Transport, insbesondere Emissionen und Energiemix."
    ),
}


def beschreibung_leistungsdimension(name: str) -> str:
    return DIMENSION_BESCHREIBUNGEN.get(name, "")
