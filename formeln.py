"""
formeln.py
===========
Formel-Kennzahlen fuer den Validierungs-Use-Case.

Der Chatbot fragt im Validierungsdurchlauf insgesamt fuenf Werte ab:
  1) Fertigungseinzelkosten pro Produktionseinheit fuer Standort A
  2) Qualitaetsrate fuer Standort A
  3) Bearbeitungszeit fuer Standort B
  4) Liegezeit fuer Standort B
  5) Gesamtenergieverbrauch fuer Standort B

Aus 1) werden die Fertigungskosten berechnet.
Aus 3) und 4) wird die Produktionsdurchlaufzeit berechnet.
Aus 5) wird der Anteil erneuerbarer Energien berechnet.
Die Qualitaetsrate wird direkt gespeichert und nicht ueber Faktoren berechnet.

Wichtig: Die Werte aus dem Validierungsleitfaden sind NICHT im Code hinterlegt.
Im Code liegen nur systemseitige Rechengroessen, die fuer die Berechnung der
abgeleiteten Kennzahlen erforderlich sind.
"""

import os
from typing import Dict, List, Optional


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _fmt_zahl(wert) -> str:
    try:
        f = float(wert)
    except (TypeError, ValueError):
        return str(wert)
    if f.is_integer():
        return f"{int(f):,}".replace(",", ".")
    return f"{f:g}".replace(".", ",")


# ---------------------------------------------------------------------------
# Systemparameter fuer die Validierung
# ---------------------------------------------------------------------------
# Die Kostenbestandteile beziehen sich jeweils auf eine Produktionseinheit.
# Dadurch entspricht die Fertigungskostenkennzahl der Summe der drei
# Kostenbestandteile je Motor.
FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT = _env_float(
    "FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT", 2_000.0
)
SONDEREINZELKOSTEN_PRO_EINHEIT = _env_float(
    "SONDEREINZELKOSTEN_PRO_EINHEIT", 800.0
)

# Der Nutzer gibt den Gesamtenergieverbrauch E_G fuer Standort B ein;
# die aus erneuerbaren Quellen stammende Energiemenge E_E liegt als
# systemseitige Rechengroesse vor.
ERNEUERBARE_ENERGIE_STANDORT_B = _env_float(
    "ERNEUERBARE_ENERGIE_STANDORT_B", 4_800_000.0
)


def _fertigungskosten(fertigungseinzelkosten_pro_einheit):
    return (
        fertigungseinzelkosten_pro_einheit
        + FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT
        + SONDEREINZELKOSTEN_PRO_EINHEIT
    )


def _produktionsdurchlaufzeit(bearbeitungszeit, liegezeit):
    return bearbeitungszeit + liegezeit


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
        "formel_text": "K_FK = B_FEK + B_FGK + B_SEK",
        "systemwerte_text": (
            f"B_FGK = {_fmt_zahl(FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT)} EUR/Stk; "
            f"B_SEK = {_fmt_zahl(SONDEREINZELKOSTEN_PRO_EINHEIT)} EUR/Stk"
        ),
    },
    "Produktionsdurchlaufzeit": {
        "optionen": ["Standort B"],
        "faktoren": [
            ("bearbeitungszeit", "Bearbeitungszeit Standort B [Tage]"),
            ("liegezeit", "Liegezeit Standort B [Tage]"),
        ],
        "funktion": _produktionsdurchlaufzeit,
        "formel_text": "K_DLZ = T_B + T_L",
        "systemwerte_text": "—",
    },
    "Anteil erneuerbarer Energien": {
        "optionen": ["Standort B"],
        "faktoren": [
            (
                "gesamtenergieverbrauch",
                "Gesamtenergieverbrauch Standort B [kWh/Jahr]",
            ),
        ],
        "funktion": _anteil_erneuerbare_energie,
        "formel_text": "K_EE = E_E / E_G × 100",
        "systemwerte_text": (
            f"E_E = {_fmt_zahl(ERNEUERBARE_ENERGIE_STANDORT_B)} kWh/Jahr"
        ),
    },
}


DIREKT_ABZUFRAGEN = {
    "Qualitätsrate": {
        "optionen": ["Standort A"],
        "beschreibung": "Qualitätsrate Standort A [%]",
    }
}


def ist_formel_kennzahl(kennzahl: str, option: Optional[str] = None) -> bool:
    definition = FORMEL_KENNZAHLEN.get(kennzahl)
    if not definition:
        return False
    return option is None or option in definition.get("optionen", [])


def berechne_formel_kennzahl(kennzahl: str, faktoren: dict):
    """Berechnet eine Formel-Kennzahl aus einem Faktoren-Dict.

    Gibt None zurueck, wenn die Kennzahl unbekannt ist oder mindestens ein
    erforderlicher Faktor fehlt.
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


def formel_hinweis_fuer_prompt(offene: Optional[Dict] = None) -> str:
    """Kompakte Beschreibung der fehlenden Werte fuer den System-Prompt."""
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
                d = DIREKT_ABZUFRAGEN[name]
                teile.append(f"- {option} / {name}: Frage direkt ab: {d['beschreibung']}.")
            else:
                teile.append(f"- {option} / {name}: Frage den Istwert direkt ab.")
    return "\n".join(teile)


def formel_liste_fuer_pdf() -> List[str]:
    return [d["formel_text"] for d in FORMEL_KENNZAHLEN.values()]


def formel_beispiele_fuer_ui() -> List[Dict]:
    """Strukturierte Formeln und Eingabehinweise fuer Streamlit/PDF.

    Die Rueckgabe enthaelt bewusst keine Beispielwerte aus dem Leitfaden.
    """
    zeilen = []
    for name, d in FORMEL_KENNZAHLEN.items():
        faktor_text = "; ".join(label for _, label in d.get("faktoren", []))
        optionen = ", ".join(d.get("optionen", []))
        zeilen.append({
            "Kennzahl": name,
            "Option": optionen,
            "Benötigte Nutzereingabe": faktor_text,
            "Formel": d.get("formel_text", ""),
            "Systemseitige Rechengrößen": d.get("systemwerte_text", ""),
        })
    for name, d in DIREKT_ABZUFRAGEN.items():
        optionen = ", ".join(d.get("optionen", []))
        zeilen.append({
            "Kennzahl": name,
            "Option": optionen,
            "Benötigte Nutzereingabe": d.get("beschreibung", ""),
            "Formel": "Direkte Nutzereingabe",
            "Systemseitige Rechengrößen": "—",
        })
    return zeilen
