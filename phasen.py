"""
phasen.py
=========
Definition der 7 Phasen des Entscheidungsprozesses. Die Phasen laufen STRIKT
nacheinander ab: erst wenn eine Phase abgeschlossen ist, wird die naechste
freigeschaltet. Der Phasen-Zaehler liegt im Sitzungsspeicher (st.session_state).

Die Texte hier werden in der Oberflaeche und teils im System-Prompt verwendet.
Anzeigenamen mit echten Umlauten.
"""

PHASEN = {
    1: {
        "titel": "1. Auswahl des Szenarios",
        "kurz": "Wir legen fest, welche Art von Entscheidung untersucht wird.",
    },
    2: {
        "titel": "2. Auswahl der Kennzahlen",
        "kurz": "Anhand der Szenario-Kennzahl-Matrix zeige ich, welche Kennzahlen "
                "relevant sind und zu welchen Leistungsdimensionen sie gehören.",
    },
    3: {
        "titel": "3. Gewichtung der Leistungsdimensionen",
        "kurz": "Du gewichtest die Dimensionen mit einem Schieberegler "
                "(Summe immer 100 %).",
    },
    4: {
        "titel": "4. Abfrage der Daten",
        "kurz": "Ich greife auf hinterlegte Beispieldaten zu und frage fehlende "
                "Werte bei dir ab.",
    },
    5: {
        "titel": "5. Berechnung der Scores",
        "kurz": "Die Nutzwerte werden transparent und deterministisch berechnet.",
    },
    6: {
        "titel": "6. Sensitivitätsanalyse",
        "kurz": "Du veränderst die Gewichtung und siehst, wie robust das Ergebnis ist.",
    },
    7: {
        "titel": "7. Ergebnis & Zusammenfassung",
        "kurz": "Du erhältst eine textliche Zusammenfassung und ein PDF zum Download.",
    },
}

ANZAHL_PHASEN = len(PHASEN)


def einfuehrungstext() -> str:
    """Kurze Einfuehrung, die der Bot zu Beginn ausgibt."""
    zeilen = [
        "**Willkommen.** Dieses Werkzeug unterstützt dich dabei, verschiedene "
        "Konfigurationen eines globalen Produktionsnetzwerks systematisch zu "
        "vergleichen und eine begründete Empfehlung abzuleiten.",
        "",
        "Wir gehen dabei in **7 Phasen** vor:",
    ]
    for i in range(1, ANZAHL_PHASEN + 1):
        zeilen.append(f"- **{PHASEN[i]['titel']}** — {PHASEN[i]['kurz']}")
    zeilen.append("")
    zeilen.append("Lass uns mit Phase 1 beginnen.")
    return "\n".join(zeilen)


def phasen_uebersicht(aktuelle_phase: int) -> str:
    """Markdown-Liste der Phasen mit Markierung der aktuellen Phase."""
    zeilen = []
    for i in range(1, ANZAHL_PHASEN + 1):
        marker = "▶️" if i == aktuelle_phase else (
            "✅" if i < aktuelle_phase else "▫️")
        zeilen.append(f"{marker} {PHASEN[i]['titel']}")
    return "\n\n".join(zeilen)
