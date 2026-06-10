"""
dimensionen.py
==============
Erklaerungen zu den Leistungsdimensionen. Diese Texte zeigt der Chatbot in
Phase 2 zusaetzlich zu den Kennzahlen an. Schluessel sind die technischen
Dimensionsnamen (ohne Umlaute), exakt wie in der Matrix.
"""

DIMENSION_BESCHREIBUNGEN = {
    "Effizienz": (
        "Die Leistungsdimension Effizienz beschreibt, in welchem Verhältnis "
        "die erbrachte Leistung eines globalen Produktionsnetzwerks zum dafür "
        "erforderlichen Ressourceneinsatz steht. Im Fokus stehen insbesondere "
        "Produktivitäts- und Kostenkennzahlen, beispielsweise "
        "Kapazitätsauslastung, Herstellkosten, Mitarbeitendenproduktivität "
        "oder Transportkosten. Für globale Produktionsnetzwerke ist Effizienz "
        "besonders relevant, da Standortentscheidungen, Kapazitätsverteilungen "
        "und interne Lieferbeziehungen direkte Auswirkungen auf Kostenstrukturen "
        "und Ressourcennutzung haben. Eine hohe Effizienz liegt vor, wenn das "
        "Netzwerk seine Produktions- und Lieferaufgaben mit möglichst geringem "
        "Einsatz von Personal, Maschinen, Flächen, Material und Kapital erfüllt."
    ),
    "Qualitaet": (
        "Die Leistungsdimension Qualität beschreibt die Fähigkeit eines globalen "
        "Produktionsnetzwerks, Produkte und Leistungen zuverlässig entsprechend "
        "definierter Anforderungen bereitzustellen. Dabei steht nicht nur die "
        "fehlerfreie Herstellung im Vordergrund, sondern auch die Einhaltung "
        "kundenseitiger Erwartungen hinsichtlich Lieferzuverlässigkeit und "
        "Prozessstabilität. Im Kontext globaler Produktionsnetzwerke ist Qualität "
        "besonders anspruchsvoll, da Produktionsprozesse, Standorte und "
        "Lieferbeziehungen über verschiedene Regionen verteilt sind. Relevante "
        "Kennzahlen sind beispielsweise Qualitätsrate, Ausschussquote, "
        "Reklamationsrate oder Liefertermintreue. Qualität bildet damit eine "
        "zentrale Voraussetzung für Kundenzufriedenheit und langfristige "
        "Wettbewerbsfähigkeit."
    ),
    "Zeit": (
        "Die Leistungsdimension Zeit bewertet, wie schnell ein globales "
        "Produktionsnetzwerk auf Kundenbedarfe, Produktionsaufträge und interne "
        "Materialflüsse reagieren kann. Im Vordergrund stehen insbesondere "
        "Durchlaufzeiten, Transportzeiten und Lieferzeiten. Diese Dimension ist "
        "für globale Produktionsnetzwerke von hoher Bedeutung, da geografisch "
        "verteilte Standorte häufig mit längeren Transportwegen, komplexeren "
        "Abstimmungsprozessen und höheren Koordinationsaufwänden verbunden sind. "
        "Eine leistungsfähige Ausprägung der Dimension Zeit zeigt sich darin, "
        "dass Produkte schnell gefertigt, standortübergreifend transportiert und "
        "termingerecht an Kunden ausgeliefert werden können."
    ),
    "Flexibilitaet": (
        "Die Leistungsdimension Flexibilität beschreibt die Fähigkeit eines "
        "globalen Produktionsnetzwerks, sich an veränderte Rahmenbedingungen "
        "anzupassen. Dazu zählen beispielsweise schwankende Nachfragevolumina, "
        "veränderte Produktvarianten, neue Marktanforderungen oder Störungen in "
        "Liefer- und Produktionsprozessen. In globalen Produktionsnetzwerken "
        "zeigt sich Flexibilität unter anderem darin, Produktionsmengen zwischen "
        "Standorten zu verlagern, verschiedene Produktvarianten an mehreren "
        "Standorten herstellen zu können oder freie Transport- und "
        "Produktionskapazitäten kurzfristig zu nutzen. Damit stellt Flexibilität "
        "eine wichtige Voraussetzung dar, um trotz dynamischer Umweltbedingungen "
        "handlungsfähig zu bleiben."
    ),
    "Oekologische Nachhaltigkeit": (
        "Die Leistungsdimension ökologische Nachhaltigkeit beschreibt die "
        "Umweltwirkungen eines globalen Produktionsnetzwerks. Sie gewinnt "
        "insbesondere deshalb an Bedeutung, weil internationale "
        "Produktionsstrukturen mit globalen Transportwegen, standortspezifischen "
        "Energiemixen und unterschiedlichen Emissionsintensitäten verbunden sind. "
        "Relevante Kennzahlen können beispielsweise CO\u2082-Emissionen aus "
        "Produktion und Transport, Energieverbrauch oder der Anteil erneuerbarer "
        "Energien sein. Im Rahmen der Netzwerkgestaltung kann ökologische "
        "Nachhaltigkeit durch die Wahl geeigneter Standorte, die Anpassung von "
        "Transportbeziehungen oder die Verlagerung energieintensiver Prozesse "
        "beeinflusst werden. Die Dimension erweitert die klassische "
        "Leistungsbewertung somit um ökologische Zielgrößen."
    ),
}


def dim_beschreibung(schluessel: str) -> str:
    return DIMENSION_BESCHREIBUNGEN.get(schluessel, "")
