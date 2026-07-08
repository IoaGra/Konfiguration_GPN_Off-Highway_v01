"""
formeln.py  (V8)
================
Kennzahlen, die im Dialog NICHT direkt, sondern ueber ihre Rohgroessen
(Faktoren) abgefragt und anschliessend deterministisch im Code berechnet
werden. Fuer den Use-Case "Verlagerung" sind das bewusst nur zwei einfache
Kennzahlen (moeglichst einfach gehalten):

  Kapazitaetsauslastung:  KA = Belegte Kapazitaet / Verfuegbare Kapazitaet x 100
  Qualitaetsrate:         QR = Gutteile / Gesamtproduktion x 100

Weitere Formel-Kennzahlen koennen hier ergaenzt werden, ohne die App zu
aendern. Die strukturellen Kennzahlen (Teileaehnlichkeit J(A,B), Abhaengige
Baureihen je Lieferant) werden VORGELAGERT in Excel berechnet (vgl. Kapitel
5.2 der Arbeit) und liegen als fertige Werte in daten.xlsx.
"""


def _ka(belegte_kapazitaet, verfuegbare_kapazitaet):
    if not verfuegbare_kapazitaet:
        return 0.0
    return belegte_kapazitaet / verfuegbare_kapazitaet * 100.0


def _qr(gutteile, gesamtproduktion):
    if not gesamtproduktion:
        return 0.0
    return gutteile / gesamtproduktion * 100.0


# Kennzahl-Name (wie in daten.xlsx) -> Definition der Abfrage-Faktoren
FORMEL_KENNZAHLEN = {
    "Kapazitätsauslastung": {
        "faktoren": [
            ("belegte_kapazitaet", "Belegte Kapazität [h/Jahr]"),
            ("verfuegbare_kapazitaet", "Verfügbare Kapazität [h/Jahr]"),
        ],
        "funktion": _ka,
        "formel_text": "KA = Belegte Kapazität / Verfügbare Kapazität × 100",
    },
    "Qualitätsrate": {
        "faktoren": [
            ("gutteile", "Gutteile [Stk/Jahr]"),
            ("gesamtproduktion", "Gesamtproduktion [Stk/Jahr]"),
        ],
        "funktion": _qr,
        "formel_text": "QR = Gutteile / Gesamtproduktion × 100",
    },
}


def berechne_formel_kennzahl(kennzahl: str, faktoren: dict):
    """Berechnet eine Formel-Kennzahl aus einem Faktoren-Dict.
    Gibt None zurueck, wenn die Kennzahl unbekannt ist oder Faktoren fehlen."""
    definition = FORMEL_KENNZAHLEN.get(kennzahl)
    if not definition:
        return None
    werte = []
    for schluessel, _ in definition["faktoren"]:
        v = faktoren.get(schluessel)
        if v is None:
            return None
        try:
            werte.append(float(v))
        except (TypeError, ValueError):
            return None
    return round(definition["funktion"](*werte), 2)


def formel_hinweis_fuer_prompt() -> str:
    """Kompakte Beschreibung der Formel-Kennzahlen fuer den System-Prompt."""
    teile = []
    for name, d in FORMEL_KENNZAHLEN.items():
        faktoren = ", ".join(f"'{s}' ({b})" for s, b in d["faktoren"])
        teile.append(f"- {name}: Frage die Faktoren {faktoren} ab. "
                     f"Formel: {d['formel_text']} (Berechnung im Code).")
    return "\n".join(teile)
