"""Deterministische Bewertungslogik des Entscheidungsmodells.

Sämtliche numerischen Ergebnisse werden in diesem Modul erzeugt. Das
Sprachmodell steuert ausschließlich den Dialog und formuliert Erläuterungen.
"""

from __future__ import annotations

from typing import Dict, Iterable, Mapping


def normiere(istwert: float, zielwert: float, grenzwert: float) -> float:
    """Normalisiert einen Istwert ziel- und grenzwertbasiert auf 0 bis 100.

    Die Wirkungsrichtung wird ausdrücklich unterschieden:
    - Zielwert > Grenzwert: höhere Werte sind besser.
    - Zielwert < Grenzwert: niedrigere Werte sind besser.
    """
    if zielwert == grenzwert:
        return 100.0 if istwert == zielwert else 0.0

    if zielwert > grenzwert:
        if istwert <= grenzwert:
            return 0.0
        if istwert >= zielwert:
            return 100.0
        return (istwert - grenzwert) / (zielwert - grenzwert) * 100.0

    if istwert <= zielwert:
        return 100.0
    if istwert >= grenzwert:
        return 0.0
    return (grenzwert - istwert) / (grenzwert - zielwert) * 100.0


def renormiere_gewichte(gewichte: Mapping[str, float]) -> Dict[str, float]:
    """Renormiert Gewichtungen auf eine Summe von 1."""
    bereinigt = {str(k): max(0.0, float(v)) for k, v in gewichte.items()}
    summe = sum(bereinigt.values())
    if summe <= 0:
        anzahl = len(bereinigt)
        return {k: 1.0 / anzahl for k in bereinigt} if anzahl else {}
    return {k: v / summe for k, v in bereinigt.items()}


def _aktive_liste(
    aktive_kennzahlen: Iterable[str] | Mapping[str, Iterable[str]],
    alternative: str,
) -> list[str]:
    if isinstance(aktive_kennzahlen, Mapping):
        return list(aktive_kennzahlen.get(alternative, []))
    return list(aktive_kennzahlen)


def berechne_nutzwerte(
    rohwerte: Dict[str, Dict[str, float]],
    aktive_kennzahlen: Iterable[str] | Mapping[str, Iterable[str]],
    kpis: Dict[str, dict],
    gewichte: Dict[str, float],
) -> dict:
    """Berechnet Normwerte, Dimensionswerte, Nutzwerte, Ränge und Empfehlung.

    ``aktive_kennzahlen`` kann entweder eine gemeinsame Kennzahlenliste oder
    eine alternativespezifische Zuordnung enthalten. Dadurch lassen sich sowohl
    verschiedene Ausprägungen desselben Szenariotyps als auch Alternativen aus
    unterschiedlichen Szenariotypen vergleichen.
    """
    optionen = list(rohwerte.keys())
    gewichte_normiert = renormiere_gewichte(gewichte)

    normwerte: Dict[str, Dict[str, float]] = {}
    dimensionswerte: Dict[str, Dict[str, float]] = {}
    nutzwerte: Dict[str, float] = {}

    for option in optionen:
        aktiv = _aktive_liste(aktive_kennzahlen, option)
        normwerte[option] = {}

        for kennzahl in aktiv:
            istwert = rohwerte.get(option, {}).get(kennzahl)
            info = kpis.get(kennzahl)
            if istwert is None or not info:
                continue
            normwerte[option][kennzahl] = round(
                normiere(
                    float(istwert),
                    float(info["zielwert"]),
                    float(info["grenzwert"]),
                ),
                2,
            )

        scores: Dict[str, float] = {}
        for dimension in gewichte_normiert:
            kennzahlen_dimension = [
                kennzahl
                for kennzahl in aktiv
                if kpis.get(kennzahl, {}).get("dimension") == dimension
                and kennzahl in normwerte[option]
            ]
            if kennzahlen_dimension:
                scores[dimension] = round(
                    sum(normwerte[option][k] for k in kennzahlen_dimension)
                    / len(kennzahlen_dimension),
                    2,
                )
        dimensionswerte[option] = scores

        if not scores:
            nutzwerte[option] = 0.0
            continue

        aktive_gewichte = renormiere_gewichte(
            {dimension: gewichte_normiert[dimension] for dimension in scores}
        )
        nutzwerte[option] = round(
            sum(scores[dimension] * aktive_gewichte[dimension] for dimension in scores),
            2,
        )

    rangliste = sorted(
        nutzwerte.items(),
        key=lambda eintrag: (-eintrag[1], eintrag[0]),
    )
    raenge = {option: rang for rang, (option, _) in enumerate(rangliste, start=1)}

    return {
        "gewichte": {d: round(g, 4) for d, g in gewichte_normiert.items()},
        "normwerte": normwerte,
        "dim_scores": dimensionswerte,
        "nutzwerte": nutzwerte,
        "raenge": raenge,
        "empfehlung": rangliste[0][0] if rangliste else None,
    }
