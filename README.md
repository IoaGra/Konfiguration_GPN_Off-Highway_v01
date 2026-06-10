# Entscheidungsmodell: globale Produktionsnetzwerke (V6)

KI-gestütztes Entscheidungstool (Streamlit + Anthropic API) für den Vergleich
von Szenarien zur Konfiguration globaler Produktionsnetzwerke.

## Dateien

| Datei | Zweck |
|---|---|
| `app.py` | Hauptanwendung: 8 Phasen (0–7), dialoggeführt, Schieberegler für Gewichtung/Sensitivität |
| `berechnung.py` | Deterministische Rechenlogik: Ziel-/Grenzwert-Normierung (0–100, gedeckelt), Aggregation, OEE |
| `daten.py` | Liest `daten.xlsx` (Ziel-/Grenzwerte, Optionswerte, fehlende Werte „/") |
| `matrix.py` | Liest `szenario_kennzahl_matrix.xlsx` (Kennzahl-Aktivierung je Szenario-Typ) |
| `szenarien.py` | Beschreibungen der Szenario-Typen (nur auf Nachfrage angezeigt) |
| `dimensionen.py` | Beschreibungen der 6 Leistungsdimensionen (nur auf Nachfrage) |
| `phasen.py` | Titel/Kurztexte der 8 Phasen |
| `pdf_export.py` | Ergebnis-PDF: Empfehlung, Nutzwerte, Gewichtung, Normwert-Tabelle, Formeln, Zusammenfassung |
| `daten.xlsx` | Datengrundlage (Beispieldaten, in Praxis aus Unternehmenssystemen) |
| `kennzahlen.xlsx` | Kennzahlen-Referenz mit Einheiten und OEE-Formel (Dokumentation) |
| `szenario_kennzahl_matrix.xlsx` | Szenario-Kennzahl-Matrix (Interdependenzen-Zeile: überall aktiv) |
| `requirements.txt` | Python-Abhängigkeiten für Streamlit Cloud |

## Architekturprinzip

„LLM as orchestrator, not as calculator": Das Sprachmodell führt den Dialog,
erfasst Werte und erklärt Ergebnisse. **Alle** Normierungen, Scores und
Nutzwerte werden ausschließlich deterministisch in `berechnung.py` berechnet.

## Normierung

Normwert = (Istwert − Grenzwert) / (Zielwert − Grenzwert) × 100, gedeckelt
auf 0–100. Die Richtung (höher/niedriger besser) ergibt sich automatisch aus
der Lage von Ziel- zu Grenzwert. Ziel- und Grenzwerte stehen in `daten.xlsx`.

## Secrets

`ANTHROPIC_API_KEY` in den Streamlit-Cloud-Secrets hinterlegen (nie im Code).
