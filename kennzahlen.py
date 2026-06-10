"""
kennzahlen.py  (V5)
===================
Deterministische Berechnungslogik fuer das MCDA-/Nutzwertanalyse-Modell.

WICHTIGE AENDERUNG GEGENUEBER FRUEHEREN VERSIONEN
-------------------------------------------------
Die Normalisierung erfolgt NICHT mehr relativ (Min-Max ueber die Szenarien),
sondern als ZIELWERT-NORMIERUNG (Distance-to-Target). Damit bleiben die Werte
absolut interpretierbar: 96 % und 98 % Qualitaet ergeben bei Zielwert 100 %
die Werte 0,96 und 0,98 - und nicht 0 und 1.

Formel je Kennzahl (Ergebnis in [0, 1], gedeckelt):
  - Nutzen (richtung 'max'):  r = min(wert / zielwert, 1)
  - Kosten (richtung 'min'):  r = min(zielwert / wert, 1)
Ein hoeherer normierter Wert ist immer besser. Der Zielwert ist der je
Kennzahl definierte Referenz-/Bestwert.

Architektur: rein deterministisch, vom LLM-Orchestrator per Function Calling
aufrufbar. Keine Seiteneffekte.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List


def _safe_div(z: float, n: float) -> float:
    return z / n if n else 0.0


# ---------------------------------------------------------------------------
#  OEE — einzige zusammengesetzte Kennzahl, deren Faktoren abgefragt werden
# ---------------------------------------------------------------------------

def oee(verfuegbarkeit: float, leistungsgrad: float, qualitaetsgrad: float) -> float:
    """OEE (%) = Verfuegbarkeit * Leistungsgrad * Qualitaetsgrad.
    Eingaben als Prozent (0..100); Rueckgabe in %.
    Quelle: Gottmann 2019 (Kap. 4.2)."""
    return (verfuegbarkeit / 100.0) * (leistungsgrad / 100.0) * \
           (qualitaetsgrad / 100.0) * 100.0


# ---------------------------------------------------------------------------
#  Zielwert-Normierung
# ---------------------------------------------------------------------------

def normalisiere_zielwert(wert: float, zielwert: float, richtung: str) -> float:
    """Zielwert-Normierung eines einzelnen Wertes auf [0, 1].

    Nutzen ('max'): r = wert / zielwert     (gedeckelt bei 1)
    Kosten ('min'): r = zielwert / wert      (gedeckelt bei 1)
    """
    if zielwert is None:
        return 0.0
    if richtung == "max":
        if zielwert <= 0:
            return 0.0
        return max(0.0, min(wert / zielwert, 1.0))
    elif richtung == "min":
        if wert <= 0:
            return 1.0
        return max(0.0, min(zielwert / wert, 1.0))
    else:
        raise ValueError(f"Unbekannte Richtung: {richtung!r}")


# ---------------------------------------------------------------------------
#  Nutzwert-Berechnung
# ---------------------------------------------------------------------------

@dataclass
class KpiDefinition:
    """Metadaten eines KPI."""
    kennzahl_id: str
    dimension: str
    richtung: str          # 'max' oder 'min'
    zielwert: float        # Bezugswert fuer die Zielwert-Normierung


def renormiere_gewichte(dimension_gewichte: Dict[str, float]) -> Dict[str, float]:
    """Renormiert Dimensionsgewichte auf Summe 1.0."""
    summe = sum(dimension_gewichte.values())
    if summe == 0:
        n = len(dimension_gewichte)
        return {d: 1.0 / n for d in dimension_gewichte} if n else {}
    return {d: g / summe for d, g in dimension_gewichte.items()}


def berechne_nutzwerte(
    rohwerte: Dict[str, Dict[str, float]],
    aktiv: Dict[str, Dict[str, int]],
    kpi_defs: Dict[str, KpiDefinition],
    dimension_gewichte: Dict[str, float],
) -> Dict[str, float]:
    """Berechnet den Nutzwert je Szenario mit Zielwert-Normierung."""
    szenarien = list(rohwerte.keys())
    nutzwerte: Dict[str, float] = {}

    for s in szenarien:
        normiert: Dict[str, float] = {}
        for kid, kdef in kpi_defs.items():
            if aktiv.get(s, {}).get(kid, 0) != 1:
                continue
            wert = rohwerte[s].get(kid)
            if wert is None:
                continue
            normiert[kid] = normalisiere_zielwert(wert, kdef.zielwert, kdef.richtung)

        dim_scores: Dict[str, float] = {}
        for dim in dimension_gewichte:
            kids = [kid for kid, kdef in kpi_defs.items()
                    if kdef.dimension == dim and kid in normiert]
            if kids:
                dim_scores[dim] = sum(normiert[kid] for kid in kids) / len(kids)

        if not dim_scores:
            nutzwerte[s] = 0.0
            continue

        aktive_gewichte = renormiere_gewichte(
            {d: dimension_gewichte[d] for d in dim_scores})
        nutzwerte[s] = sum(dim_scores[d] * aktive_gewichte[d] for d in dim_scores)

    return nutzwerte
