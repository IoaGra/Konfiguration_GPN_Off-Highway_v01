"""
anzeige.py
==========
Zuordnung von internen (technischen) Schluesseln zu Anzeigenamen MIT
Umlauten. Die internen Schluessel (Dimensionsnamen als dict-Keys,
kennzahl_id) bleiben technisch ohne Umlaute, damit nichts an Tippfehlern
oder Kodierung scheitert. Nur die SICHTBAREN Texte tragen echte Umlaute.
"""

# Dimension (technischer Schluessel) -> Anzeigename mit Umlauten
DIMENSION_ANZEIGE = {
    "Qualitaet": "Qualität",
    "Zeit": "Zeit",
    "Flexibilitaet": "Flexibilität",
    "Effizienz": "Effizienz",
    "Oekologische Nachhaltigkeit": "Ökologische Nachhaltigkeit",
}


def dim_anzeige(schluessel: str) -> str:
    """Anzeigename einer Dimension (mit Umlaut), faellt auf den Schluessel zurueck."""
    return DIMENSION_ANZEIGE.get(schluessel, schluessel)
