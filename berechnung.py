# =============================================================
#  DETERMINISTISCHE BERECHNUNGSLOGIK
# =============================================================
#  Dies ist der wissenschaftliche Kern des Modells.
#  ALLE Formeln werden hier in Python berechnet - NICHT vom
#  Sprachmodell. Dadurch sind die Ergebnisse reproduzierbar.
#
#  Enthaltene Formeln:
#   1. Min-Max-Normalisierung (relativ, je Kennzahl)
#   2. Aggregation Kennzahlen -> Dimension (arithm. Mittel)
#   3. Aggregation Dimensionen -> Gesamtnutzwert (gewichtet)
#   4. Datenqualitaetsindex (Variante A: getrenntes Reporting)
#   5. Re-Normalisierung der Nutzergewichte (Summe = 1)
# =============================================================

from config import DIMENSIONEN


def renormiere_gewichte(roh_gewichte: dict) -> dict:
    """Stellt sicher, dass die Summe der Gewichte = 1 ist.
    Formel:  W_d = W_d_roh / Summe(W_d_roh)"""
    summe = sum(roh_gewichte.values())
    if summe == 0:
        # Fallback: Gleichverteilung
        n = len(roh_gewichte)
        return {d: 1.0 / n for d in roh_gewichte}
    return {d: w / summe for d, w in roh_gewichte.items()}


def normalisiere(rohwerte: list, richtung: str) -> list:
    """Min-Max-Normalisierung einer Kennzahl ueber alle Szenarien.
    Nutzen:  r = (x - min) / (max - min)
    Kosten:  r = (max - x) / (max - min)
    Sonderfall: sind alle Werte gleich, wird 1.0 vergeben
    (kein Unterschied zwischen den Szenarien)."""
    x_min = min(rohwerte)
    x_max = max(rohwerte)
    spanne = x_max - x_min
    if spanne == 0:
        return [1.0 for _ in rohwerte]
    if richtung == "nutzen":
        return [(x - x_min) / spanne for x in rohwerte]
    else:  # kosten
        return [(x_max - x) / spanne for x in rohwerte]


def berechne(szenarien: dict, roh_gewichte: dict) -> dict:
    """Hauptfunktion. Berechnet Nutzwert und Datenqualitaet je Szenario.

    Erwartetes Format von 'szenarien':
    {
      "Szenario A": {
         "Effizienz": {
            "Kapazitaetsauslastung": {"wert": 85.0, "quelle_q": 1.0},
            "Stueckkosten":          {"wert": 12.5, "quelle_q": 0.7},
            ...
         },
         "Qualitaet": { ... },
         ...
      },
      "Szenario B": { ... }
    }

    'roh_gewichte': {"Effizienz": 0.2, "Qualitaet": 0.2, ...}

    Rueckgabe je Szenario: Nutzwert, Datenqualitaet, Dimensions-Scores.
    """
    namen = list(szenarien.keys())
    gewichte = renormiere_gewichte(roh_gewichte)

    # --- Schritt 1: Normalisierung je Kennzahl ueber alle Szenarien ---
    # normalisiert[dim][kennzahl] = {szenario: r_wert}
    normalisiert = {}
    for dim, inhalt in DIMENSIONEN.items():
        normalisiert[dim] = {}
        for kz in inhalt["kennzahlen"]:
            kz_name = kz["name"]
            rohwerte = [szenarien[s][dim][kz_name]["wert"] for s in namen]
            norm = normalisiere(rohwerte, kz["richtung"])
            normalisiert[dim][kz_name] = dict(zip(namen, norm))

    # --- Schritt 2 & 3: Aggregation je Szenario ---
    ergebnis = {}
    for s in namen:
        nutzwert = 0.0
        qualitaet = 0.0
        dim_scores = {}
        for dim, inhalt in DIMENSIONEN.items():
            kennzahlen = inhalt["kennzahlen"]
            n_d = len(kennzahlen)

            # arithmetisches Mittel der normalisierten Kennzahlen
            d_score = sum(normalisiert[dim][kz["name"]][s] for kz in kennzahlen) / n_d
            # arithmetisches Mittel der Datenqualitaet in dieser Dimension
            q_score = sum(szenarien[s][dim][kz["name"]]["quelle_q"] for kz in kennzahlen) / n_d

            dim_scores[dim] = round(d_score, 4)
            nutzwert += gewichte[dim] * d_score
            qualitaet += gewichte[dim] * q_score

        ergebnis[s] = {
            "nutzwert": round(nutzwert, 4),
            "datenqualitaet": round(qualitaet, 4),
            "dimensionen": dim_scores,
        }

    # --- Rangfolge nach Nutzwert ---
    rangliste = sorted(ergebnis.items(), key=lambda kv: kv[1]["nutzwert"], reverse=True)
    for rang, (s, _) in enumerate(rangliste, start=1):
        ergebnis[s]["rang"] = rang

    return {
        "gewichte": {d: round(w, 4) for d, w in gewichte.items()},
        "szenarien": ergebnis,
        "empfehlung": rangliste[0][0],
    }
