"""
berechnung.py  (V6)
===================
Deterministische Berechnungslogik. ALLE Zahlen entstehen hier im Code -
niemals im Sprachmodell ("LLM as orchestrator, not as calculator").

NORMIERUNG (Ziel-/Grenzwert-Verfahren, Skala 0-100)
---------------------------------------------------
    Normwert = (Istwert - Grenzwert) / (Zielwert - Grenzwert) * 100

Diese eine Formel deckt beide Richtungen ab:
  - hoeher ist besser:  Zielwert > Grenzwert  -> besserer Istwert => hoeherer Normwert
  - geringer ist besser: Zielwert < Grenzwert -> kleinerer Istwert => hoeherer Normwert
Normwerte werden auf [0, 100] gedeckelt (Werte ausserhalb des
Ziel-Grenz-Korridors zaehlen als 0 bzw. 100).

AGGREGATION
-----------
  Dimensions-Score = Mittelwert der Normwerte der aktiven Kennzahlen
                     (Kennzahlen innerhalb einer Dimension gleichgewichtet)
  Nutzwert         = Summe( Gewicht_Dimension * Dimensions-Score ),
                     Gewichte auf Summe 1 renormiert.

OEE (einzige Formel-Kennzahl, Quelle: kennzahlen.xlsx)
------------------------------------------------------
  OEE (%) = Anlagenverfuegbarkeit * Anlageneffizienz * Qualitaetsgrad
  (Faktoren jeweils in %, Ergebnis in %)
"""

from __future__ import annotations
from typing import Dict


def oee(anlagenverfuegbarkeit: float, anlageneffizienz: float,
        qualitaetsgrad: float) -> float:
    """OEE (%) aus drei Faktoren (jeweils in %)."""
    return (anlagenverfuegbarkeit / 100.0) * (anlageneffizienz / 100.0) * \
           (qualitaetsgrad / 100.0) * 100.0


def normiere(istwert: float, zielwert: float, grenzwert: float) -> float:
    """Ziel-/Grenzwert-Normierung auf [0, 100], gedeckelt.

    Normwert = (Ist - Grenz) / (Ziel - Grenz) * 100
    """
    spanne = zielwert - grenzwert
    if spanne == 0:
        return 100.0 if istwert == zielwert else 0.0
    norm = (istwert - grenzwert) / spanne * 100.0
    return max(0.0, min(norm, 100.0))


def renormiere_gewichte(gewichte: Dict[str, float]) -> Dict[str, float]:
    """Gewichte auf Summe 1 renormieren."""
    summe = sum(gewichte.values())
    if summe == 0:
        n = len(gewichte)
        return {d: 1.0 / n for d in gewichte} if n else {}
    return {d: g / summe for d, g in gewichte.items()}


def berechne_nutzwerte(
    rohwerte: Dict[str, Dict[str, float]],
    aktive_kennzahlen: list,
    kpis: Dict[str, dict],
    gewichte: Dict[str, float],
) -> dict:
    """Vollstaendige Berechnung fuer alle Optionen.

    rohwerte          : {option: {kennzahl: istwert}}
    aktive_kennzahlen : Liste der fuer den Szenario-Typ aktiven Kennzahlen
    kpis              : {kennzahl: {dimension, einheit, zielwert, grenzwert}}
    gewichte          : {dimension: gewicht}  (werden renormiert)

    Rueckgabe (vollstaendig dokumentiert fuer die Transparenz-Darstellung):
    {
      "gewichte":   {dimension: gewicht_normiert},
      "normwerte":  {option: {kennzahl: normwert}},
      "dim_scores": {option: {dimension: score}},
      "nutzwerte":  {option: nutzwert},
      "raenge":     {option: rang},
      "empfehlung": option,
    }
    """
    optionen = list(rohwerte.keys())
    gewichte_n = renormiere_gewichte(gewichte)

    normwerte = {}
    dim_scores = {}
    nutzwerte = {}

    for opt in optionen:
        normwerte[opt] = {}
        for k in aktive_kennzahlen:
            ist = rohwerte[opt].get(k)
            if ist is None:
                continue
            info = kpis[k]
            normwerte[opt][k] = round(
                normiere(ist, info["zielwert"], info["grenzwert"]), 2)

        # Dimensions-Scores: Mittelwert der Normwerte je Dimension
        scores = {}
        for dim in gewichte_n:
            kz = [k for k in aktive_kennzahlen
                  if kpis[k]["dimension"] == dim and k in normwerte[opt]]
            if kz:
                scores[dim] = round(
                    sum(normwerte[opt][k] for k in kz) / len(kz), 2)
        dim_scores[opt] = scores

        if not scores:
            nutzwerte[opt] = 0.0
            continue

        # Dimensionen ohne aktive Kennzahlen fair herausrechnen
        aktive_gewichte = renormiere_gewichte(
            {d: gewichte_n[d] for d in scores})
        nutzwerte[opt] = round(
            sum(scores[d] * aktive_gewichte[d] for d in scores), 2)

    rangliste = sorted(nutzwerte.items(), key=lambda kv: kv[1], reverse=True)
    raenge = {o: i + 1 for i, (o, _) in enumerate(rangliste)}

    return {
        "gewichte": {d: round(g, 4) for d, g in gewichte_n.items()},
        "normwerte": normwerte,
        "dim_scores": dim_scores,
        "nutzwerte": nutzwerte,
        "raenge": raenge,
        "empfehlung": rangliste[0][0] if rangliste else None,
    }
