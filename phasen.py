"""
phasen.py
==========
Phasen des validierungsorientierten Entscheidungsprozesses.

Die Auswahl der relevanten Kennzahlen findet intern über die
Szenario-Kennzahl-Matrix statt und wird dem Nutzer erst in der
Datenabfrage kompakt erläutert.
"""

PHASEN = {
    0: {"titel": "0. Einstieg & Erklärung",
        "kurz": "Ich erkläre kurz Ziel, Ablauf und Ergebnis des Entscheidungsprozesses."},
    1: {"titel": "1. Auswahl des Szenarios",
        "kurz": "Du legst den Szenario-Typ und die zu vergleichenden Optionen fest."},
    2: {"titel": "2. Gewichtung der Leistungsdimensionen",
        "kurz": "Du gewichtest die fünf Leistungsdimensionen mit Schiebereglern."},
    3: {"titel": "3. Abfrage der Daten",
        "kurz": "Vorhandene Systemdaten werden angezeigt; fehlende Werte werden gezielt abgefragt."},
    4: {"titel": "4. Berechnung der Scores",
        "kurz": "Normwerte, Dimensions-Scores und Nutzwerte werden deterministisch berechnet."},
    5: {"titel": "5. Sensitivitätsanalyse",
        "kurz": "Du variierst die Gewichtung und prüfst die Robustheit der Empfehlung."},
    6: {"titel": "6. Zusammenfassung & Ergebnis",
        "kurz": "Die finale Zusammenfassung und die Ergebnis-PDF werden erstellt."},
}

ANZAHL_PHASEN = len(PHASEN)
