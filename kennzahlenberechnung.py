"""Berechnung abgeleiteter Kennzahlen und Beschreibung ihrer Eingabefaktoren.

Die Werte des Validierungsleitfadens sind nicht im Quellcode hinterlegt. Im
Code befinden sich ausschließlich systemseitige Rechengrößen, die zur
Berechnung der abgeleiteten Kennzahlen benötigt werden.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional


def _umgebungswert(name: str, standard: float) -> float:
    try:
        return float(os.getenv(name, standard))
    except (TypeError, ValueError):
        return standard


def _format_zahl(wert: float) -> str:
    zahl = float(wert)
    if zahl.is_integer():
        return f"{int(zahl):,}".replace(",", ".")
    return f"{zahl:g}".replace(".", ",")


FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT = _umgebungswert(
    "FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT", 2_000.0
)
SONDEREINZELKOSTEN_PRO_EINHEIT = _umgebungswert(
    "SONDEREINZELKOSTEN_PRO_EINHEIT", 800.0
)
ERNEUERBARE_ENERGIE_STANDORT_B = _umgebungswert(
    "ERNEUERBARE_ENERGIE_STANDORT_B", 4_800_000.0
)


def _fertigungskosten(fertigungseinzelkosten_pro_einheit: float) -> float:
    return (
        fertigungseinzelkosten_pro_einheit
        + FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT
        + SONDEREINZELKOSTEN_PRO_EINHEIT
    )


def _produktionsdurchlaufzeit(
    bearbeitungszeit: float,
    liegezeit: float,
) -> float:
    return bearbeitungszeit + liegezeit


def _anteil_erneuerbarer_energien(gesamtenergieverbrauch: float) -> float:
    if gesamtenergieverbrauch <= 0:
        raise ValueError("Der Gesamtenergieverbrauch muss größer als null sein.")
    return ERNEUERBARE_ENERGIE_STANDORT_B / gesamtenergieverbrauch * 100.0


FORMEL_KENNZAHLEN = {
    "Fertigungskosten": {
        "datenoptionen": ["Standort A"],
        "faktoren": [
            (
                "fertigungseinzelkosten_pro_einheit",
                "Fertigungseinzelkosten pro Produktionseinheit",
                "EUR/Stk",
            ),
        ],
        "funktion": _fertigungskosten,
        "formel_text": "K_FK = B_FEK + B_FGK + B_SEK",
        "systemwerte_text": (
            f"B_FGK = {_format_zahl(FERTIGUNGSGEMEINKOSTEN_PRO_EINHEIT)} EUR/Stk; "
            f"B_SEK = {_format_zahl(SONDEREINZELKOSTEN_PRO_EINHEIT)} EUR/Stk"
        ),
    },
    "Produktionsdurchlaufzeit": {
        "datenoptionen": ["Standort B"],
        "faktoren": [
            ("bearbeitungszeit", "Bearbeitungszeit", "Tage"),
            ("liegezeit", "Liegezeit", "Tage"),
        ],
        "funktion": _produktionsdurchlaufzeit,
        "formel_text": "K_DLZ = T_B + T_L",
        "systemwerte_text": "—",
    },
    "Anteil erneuerbarer Energien": {
        "datenoptionen": ["Standort B"],
        "faktoren": [
            (
                "gesamtenergieverbrauch",
                "Gesamtenergieverbrauch",
                "kWh/Jahr",
            ),
        ],
        "funktion": _anteil_erneuerbarer_energien,
        "formel_text": "K_EE = E_E / E_G × 100",
        "systemwerte_text": (
            f"E_E = {_format_zahl(ERNEUERBARE_ENERGIE_STANDORT_B)} kWh/Jahr"
        ),
    },
}


def formel_definition(
    kennzahl: str,
    datenoption: Optional[str] = None,
) -> Optional[dict]:
    definition = FORMEL_KENNZAHLEN.get(kennzahl)
    if not definition:
        return None
    if datenoption is None:
        return definition
    if datenoption not in definition.get("datenoptionen", []):
        return None
    return definition


def ist_formel_kennzahl(kennzahl: str, datenoption: Optional[str] = None) -> bool:
    return formel_definition(kennzahl, datenoption) is not None


def faktoren_fuer(kennzahl: str, datenoption: Optional[str] = None) -> list[tuple]:
    definition = formel_definition(kennzahl, datenoption)
    return list(definition.get("faktoren", [])) if definition else []


def faktor_information(
    kennzahl: str,
    faktor_schluessel: str,
    datenoption: Optional[str] = None,
) -> Optional[tuple[str, str]]:
    for schluessel, bezeichnung, einheit in faktoren_fuer(kennzahl, datenoption):
        if schluessel == faktor_schluessel:
            return bezeichnung, einheit
    return None


def naechster_fehlender_faktor(
    kennzahl: str,
    vorhandene_faktoren: dict,
    datenoption: Optional[str] = None,
) -> Optional[str]:
    for schluessel, _, _ in faktoren_fuer(kennzahl, datenoption):
        if schluessel not in vorhandene_faktoren:
            return schluessel
    return None


def berechne_formel_kennzahl(
    kennzahl: str,
    faktoren: dict,
    datenoption: Optional[str] = None,
) -> Optional[float]:
    definition = formel_definition(kennzahl, datenoption)
    if not definition:
        return None

    werte = []
    for schluessel, _, _ in definition["faktoren"]:
        wert = faktoren.get(schluessel)
        if wert is None:
            return None
        try:
            werte.append(float(wert))
        except (TypeError, ValueError):
            return None

    try:
        return round(float(definition["funktion"](*werte)), 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def formel_uebersicht_fuer_ui() -> List[Dict]:
    """Erzeugt eine UI-Tabelle ohne Validierungsbeispielwerte."""
    zeilen: List[Dict] = []
    for kennzahl, definition in FORMEL_KENNZAHLEN.items():
        faktoren = "; ".join(
            f"{bezeichnung} [{einheit}]"
            for _, bezeichnung, einheit in definition.get("faktoren", [])
        )
        zeilen.append(
            {
                "Kennzahl": kennzahl,
                "Berechnung verfügbar für": ", ".join(
                    definition.get("datenoptionen", [])
                ),
                "Benötigte Teilwerte": faktoren,
                "Formel": definition.get("formel_text", ""),
                "Systemseitige Rechengrößen": definition.get(
                    "systemwerte_text", "—"
                ),
                "Alternative Eingabe": "Istwert kann direkt angegeben werden",
            }
        )
    return zeilen


def formel_liste_fuer_pdf() -> List[str]:
    return [definition["formel_text"] for definition in FORMEL_KENNZAHLEN.values()]
