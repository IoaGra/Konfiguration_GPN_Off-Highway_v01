"""
formeln.py
==========
Formel-Kennzahlen für den Validierungs-Use-Case.

Der Nutzer gibt im Validierungsdurchlauf genau drei Werte ein:
  1) Fertigungseinzelkosten pro Produktionseinheit für Standort A
  2) Qualitätsrate für Standort A
  3) Gesamtenergieverbrauch für Standort B

Aus 1) werden die Fertigungskosten berechnet.
Aus 3) wird der Anteil erneuerbarer Energie berechnet.
Die Qualitätsrate wird direkt gespeichert und nicht über Faktoren berechnet.

Wichtig:
Die Systemparameter unten müssen zu deinem Leitfaden passen. Alternativ können
sie über Umgebungsvariablen gesetzt werden, z. B. in Streamlit Secrets.
"""

from __future__ import annotations
import os


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Systemparameter für die Validierung
# ---------------------------------------------------------------------------
# Formel aus Kapitel 5:
# K_FK = (B_FEK + B_FGK + B_SEK) / P_S
# Da der Nutzer B_FEK bereits je Produktionseinheit eingibt, werden die
# Gemeinkosten und Sondereinzelkosten ebenfalls als EUR/Stk hinterlegt.
FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT = _env_float(
    "FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT", 0.0
)
SONDEREINZELKOSTEN_PRO_EINHEIT = _env_float(
    "SONDEREINZELKOSTEN_PRO_EINHEIT", 0.0
)

# Formel aus Kapitel 5:
# K_EE = E_E / E_G * 100
# Der Nutzer gibt E_G für Standort B ein; E_E wird als Systemwert hinterlegt.
ERNEUERBARE_ENERGIE_STANDORT_B = _env_float(
    "ERNEUERBARE_ENERGIE_STANDORT_B", 0.0
)


def _fertigungskosten(fertigungseinzelkosten_pro_einheit):
    return (
        fertigungseinzelkosten_pro_einheit
        + FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT
        + SONDEREINZELKOSTEN_PRO_EINHEIT
    )


def _anteil_erneuerbare_energie(gesamtenergieverbrauch):
    if not gesamtenergieverbrauch:
        return 0.0
    return ERNEUERBARE_ENERGIE_STANDORT_B / gesamtenergieverbrauch * 100.0


FORMEL_KENNZAHLEN = {
    "Fertigungskosten": {
        "optionen": ["Standort A"],
        "faktoren": [
            (
                "fertigungseinzelkosten_pro_einheit",
                "Fertigungseinzelkosten pro Produktionseinheit [EUR/Stk]",
            ),
        ],
        "funktion": _fertigungskosten,
        "formel_text": (
            "K_FK = Fertigungseinzelkosten je Produktionseinheit "
            "+ Fertigungsgemeinkosten je Produktionseinheit "
            "+ Sondereinzelkosten je Produktionseinheit"
        ),
    },
    "Anteil erneuerbarer Energien": {
        "optionen": ["Standort B"],
        "faktoren": [
            (
                "gesamtenergieverbrauch",
                "Gesamtenergieverbrauch Standort B [z. B. kWh/Jahr]",
            ),
        ],
        "funktion": _anteil_erneuerbare_energie,
        "formel_text": "K_EE = Erneuerbare Energie / Gesamtenergieverbrauch × 100",
    },
}


DIREKT_ABZUFRAGEN = {
    "Qualitätsrate": {
        "optionen": ["Standort A"],
        "beschreibung": "Qualitätsrate Standort A [%]",
    }
}


def ist_formel_kennzahl(kennzahl: str, option: str | None = None) -> bool:
    definition = FORMEL_KENNZAHLEN.get(kennzahl)
    if not definition:
        return False
    return option is None or option in definition.get("optionen", [])


def berechne_formel_kennzahl(kennzahl: str, faktoren: dict):
    """Berechnet eine Formel-Kennzahl aus einem Faktoren-Dict.
    Gibt None zurück, wenn die Kennzahl unbekannt ist oder Faktoren fehlen.
    """
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


def formel_hinweis_fuer_prompt(offene: dict | None = None) -> str:
    """Kompakte Beschreibung der fehlenden Werte für den System-Prompt."""
    teile = []
    offene = offene or {}
    for option, kennzahlen in offene.items():
        for name in kennzahlen:
            if ist_formel_kennzahl(name, option):
                d = FORMEL_KENNZAHLEN[name]
                faktoren = ", ".join(f"'{s}' ({b})" for s, b in d["faktoren"])
                teile.append(
                    f"- {option} / {name}: Frage die Faktoren {faktoren} ab. "
                    f"Formel: {d['formel_text']} (Berechnung im Code)."
                )
            elif name in DIREKT_ABZUFRAGEN:
                beschr = DIREKT_ABZUFRAGEN[name]["beschreibung"]
                teile.append(f"- {option} / {name}: Frage direkt ab: {beschr}.")
            else:
                teile.append(f"- {option} / {name}: Frage den Istwert direkt ab.")
    return "\n".join(teile)


def formel_liste_fuer_pdf() -> list[str]:
    return [d["formel_text"] for d in FORMEL_KENNZAHLEN.values()]
