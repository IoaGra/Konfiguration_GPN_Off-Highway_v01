# =============================================================
#  KONFIGURATION DES ENTSCHEIDUNGSMODELLS
# =============================================================
#  Hier definierst du die Leistungsdimensionen und ihre
#  Kennzahlen (KPIs). Du kannst spaeter ohne Programmier-
#  kenntnisse Dimensionen oder Kennzahlen ergaenzen, indem du
#  diese Liste erweiterst. Achte nur auf die gleiche Struktur
#  und die Kommata.
#
#  Bedeutung der Felder pro Kennzahl:
#    "name"        = Anzeigename der Kennzahl
#    "richtung"    = "nutzen"  -> hoeherer Wert ist besser
#                    "kosten"  -> niedrigerer Wert ist besser
#    "einheit"     = nur zur Anzeige (z. B. "%", "EUR", "Tage")
# =============================================================

DIMENSIONEN = {
    "Effizienz": {
        "kennzahlen": [
            {"name": "Kapazitaetsauslastung", "richtung": "nutzen", "einheit": "%"},
            {"name": "Stueckkosten",          "richtung": "kosten", "einheit": "EUR"},
            {"name": "Produktivitaet",        "richtung": "nutzen", "einheit": "Stk/h"},
        ]
    },
    "Qualitaet": {
        "kennzahlen": [
            {"name": "Ausschussquote",        "richtung": "kosten", "einheit": "%"},
            {"name": "Erstausbeute (FPY)",    "richtung": "nutzen", "einheit": "%"},
        ]
    },
    "Zeit": {
        "kennzahlen": [
            {"name": "Durchlaufzeit",         "richtung": "kosten", "einheit": "Tage"},
            {"name": "Liefertreue",           "richtung": "nutzen", "einheit": "%"},
        ]
    },
    "Flexibilitaet": {
        "kennzahlen": [
            {"name": "Ruestzeit",             "richtung": "kosten", "einheit": "Min"},
            {"name": "Volumenflexibilitaet",  "richtung": "nutzen", "einheit": "%"},
        ]
    },
    "Oekologische Nachhaltigkeit": {
        "kennzahlen": [
            {"name": "CO2-Ausstoss",          "richtung": "kosten", "einheit": "t/Jahr"},
            {"name": "Recyclingquote",        "richtung": "nutzen", "einheit": "%"},
        ]
    },
}

# -------------------------------------------------------------
#  STARTGEWICHTE der Dimensionen (Summe wird automatisch auf 1
#  normiert). Gleichverteilung ist als Standard hinterlegt.
# -------------------------------------------------------------
STARTGEWICHTE = {
    "Effizienz": 0.20,
    "Qualitaet": 0.20,
    "Zeit": 0.20,
    "Flexibilitaet": 0.20,
    "Oekologische Nachhaltigkeit": 0.20,
}

# -------------------------------------------------------------
#  DATENQUALITAETS-STUFEN (Variante A: reines Reporting).
#  Diese Werte fliessen NICHT in den Nutzwert ein, sondern
#  werden getrennt als Konfidenzmass ausgewiesen.
# -------------------------------------------------------------
DATENQUALITAET = {
    "Nutzereingabe":          1.0,   # vom Nutzer direkt eingegeben
    "Dokumentenextraktion":   0.7,   # vom Bot aus Dokument extrahiert
    "Schaetzung (worst case)": 0.3,  # vom Bot geschaetzt
}
