"""Definition der sieben streng sequenziell durchlaufenen Prozessphasen."""

PHASEN = {
    0: {
        "titel": "0. Einstieg und Erklärung",
        "kurz": "Zweck und Ablauf des Entscheidungsprozesses.",
        "beschreibung": (
            "Die nutzende Person erhält allgemeine Informationen zum Zweck, "
            "zur Zielsetzung und zum Ablauf des Entscheidungsmodells."
        ),
    },
    1: {
        "titel": "1. Konkretisierung der Entscheidungssituation",
        "kurz": "Festlegung der zu vergleichenden Handlungsalternativen.",
        "beschreibung": (
            "Mindestens zwei Handlungsalternativen werden vollständig definiert. "
            "Dabei sind unterschiedliche Szenariotypen oder unterschiedliche "
            "Ausprägungen desselben Szenariotyps möglich."
        ),
    },
    2: {
        "titel": "2. Gewichtung der Leistungsdimensionen",
        "kurz": "Festlegung der fünf Gewichtungsfaktoren.",
        "beschreibung": (
            "Die Leistungsdimensionen werden mit Faktoren zwischen 0 und 1 "
            "gewichtet; ihre Summe beträgt stets 1."
        ),
    },
    3: {
        "titel": "3. Zusammenstellung der Datengrundlage",
        "kurz": "Ergänzung der relevanten Kennzahlenwerte.",
        "beschreibung": (
            "Vorhandene Systemwerte werden übernommen. Fehlende Werte können "
            "direkt angegeben oder anhand hinterlegter Formeln berechnet werden."
        ),
    },
    4: {
        "titel": "4. Mathematische Bewertung",
        "kurz": "Normalisierung, Aggregation und Rangbildung.",
        "beschreibung": (
            "Die Kennzahlen werden normalisiert, zu Leistungsdimensionen "
            "aggregiert und zu Gesamtnutzwerten zusammengeführt."
        ),
    },
    5: {
        "titel": "5. Sensitivitätsanalyse",
        "kurz": "Prüfung der Stabilität bei veränderten Gewichtungen.",
        "beschreibung": (
            "Alternative Gewichtungen werden getestet, ohne die ursprüngliche "
            "Bewertung zu überschreiben."
        ),
    },
    6: {
        "titel": "6. Zusammenfassung und Ergebnis",
        "kurz": "Zusammenfassung, Empfehlung und PDF-Ausgabe.",
        "beschreibung": (
            "Auswahl, Datengrundlage, Ergebnisse und Erkenntnisse der "
            "Sensitivitätsanalyse werden zusammengeführt."
        ),
    },
}

ANZAHL_PHASEN = len(PHASEN)
