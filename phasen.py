"""Phasen des validierungsorientierten Entscheidungsprozesses."""

PHASEN = {
    0: {
        "titel": "0. Einstieg und Erklärung",
        "kurz": "Ziel, Ablauf und Ergebnis des Entscheidungsprozesses werden erläutert.",
    },
    1: {
        "titel": "1. Auswahl des Szenarios",
        "kurz": "Szenario-Typ, betroffene Baureihe und Vergleichsoptionen werden festgelegt.",
    },
    2: {
        "titel": "2. Gewichtung der Leistungsdimensionen",
        "kurz": "Die fünf Leistungsdimensionen werden mit Schiebereglern gewichtet.",
    },
    3: {
        "titel": "3. Abfrage der Daten",
        "kurz": "Systemdaten werden zusammengeführt und fehlende Werte einzeln ergänzt.",
    },
    4: {
        "titel": "4. Berechnung der Scores",
        "kurz": "Normwerte, Werte der Leistungsdimensionen und Nutzwerte werden berechnet.",
    },
    5: {
        "titel": "5. Sensitivitätsanalyse",
        "kurz": "Veränderte Gewichtungen prüfen die Robustheit der Empfehlung.",
    },
    6: {
        "titel": "6. Zusammenfassung und Ergebnis",
        "kurz": "Gewichtungen, Ergebnisse, Interpretation und PDF werden ausgegeben.",
    },
}

ANZAHL_PHASEN = len(PHASEN)
