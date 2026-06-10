"""
phasen.py  (V6)
===============
Die 8 Phasen (0-7) des Entscheidungsprozesses. Phase 0 ist der Einstieg;
die Sensitivitaetsanalyse ist eine eigene Phase (6) zwischen Berechnung
und Zusammenfassung.
"""

PHASEN = {
    0: {"titel": "0. Einstieg & Erklärung",
        "kurz": "Ich erkläre dir kurz das Vorgehen und was dich erwartet."},
    1: {"titel": "1. Auswahl der Szenarien",
        "kurz": "Du wählst den Szenario-Typ und mindestens zwei Ausprägungen "
                "(z. B. Standorte), die verglichen werden sollen."},
    2: {"titel": "2. Auswahl der Kennzahlen",
        "kurz": "Anhand der Szenario-Kennzahl-Matrix zeige ich, welche "
                "Kennzahlen relevant sind."},
    3: {"titel": "3. Gewichtung der Leistungsdimensionen",
        "kurz": "Du gewichtest die sechs Leistungsdimensionen mit "
                "Schiebereglern (Summe immer 100 %)."},
    4: {"titel": "4. Abfrage der Daten",
        "kurz": "Ich hole vorhandene Daten aus dem System und frage "
                "fehlende Werte gezielt bei dir ab."},
    5: {"titel": "5. Berechnung der Scores",
        "kurz": "Die Normwerte und Nutzwerte werden transparent und "
                "deterministisch im Code berechnet."},
    6: {"titel": "6. Sensitivitätsanalyse",
        "kurz": "Du veränderst die Gewichtung und prüfst, wie robust das "
                "Ergebnis ist."},
    7: {"titel": "7. Zusammenfassung & Ergebnis",
        "kurz": "Detaillierte Zusammenfassung entlang der Phasen, inkl. "
                "Formeln, plus PDF-Download."},
}

ANZAHL_PHASEN = len(PHASEN)  # 8 (0..7)
