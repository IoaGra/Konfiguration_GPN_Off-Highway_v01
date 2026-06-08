"""
matrix.py
=========
Liest die Szenario-Kennzahl-Matrix (CSV, semikolongetrennt) ein und stellt
Hilfsfunktionen bereit, die der Chatbot und die Berechnung nutzen.

Die Matrix legt je Szenario-TYP fest, welche Kennzahlen relevant ("strikt")
sind. Der Nutzer waehlt zu Beginn EINEN Szenario-Typ; danach sind nur die in
dieser Spalte mit 1 markierten Kennzahlen aktiv.

Erwartetes CSV-Format (Spalten):
  dimension; kennzahl; kennzahl_id; quelle; einheit; richtung; <typ1>; <typ2>; ...
"""

import csv
from kennzahlen import KpiDefinition

# feste Spalten, die KEINE Szenario-Typen sind
_FIXE_SPALTEN = {"dimension", "kennzahl", "kennzahl_id", "quelle", "einheit", "richtung"}

# Anzeigenamen fuer die Szenario-Typen (Spaltenname -> lesbarer Name)
SZENARIO_TYP_LABELS = {
    "verlagerung": "Standortverlagerung",
    "lieferantenwechsel": "Lieferantenwechsel",
    "sop_neu": "Start of Production (neuer Standort)",
    "make_or_buy": "Make-or-Buy",
    "eop_restvolumen": "End of Production / Restvolumen",
    "referenz": "Referenz (keine Aenderung)",
}


def lade_matrix(pfad: str = "szenario_kennzahl_matrix.csv"):
    """Liest die Matrix und gibt vier Strukturen zurueck:

    szenario_typen : Liste der Typ-Spalten (z.B. ['verlagerung', ...])
    kpi_defs       : {kennzahl_id: KpiDefinition(dimension, richtung)}
    matrix         : {kennzahl_id: {typ: 0|1}}
    meta           : {kennzahl_id: {name, einheit, dimension, quelle}}
    """
    with open(pfad, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        zeilen = list(reader)
        feldnamen = reader.fieldnames

    szenario_typen = [c for c in feldnamen if c not in _FIXE_SPALTEN]

    kpi_defs, matrix, meta = {}, {}, {}
    for z in zeilen:
        kid = z["kennzahl_id"].strip()
        if not kid:
            continue
        kpi_defs[kid] = KpiDefinition(
            kennzahl_id=kid,
            dimension=z["dimension"].strip(),
            richtung=z["richtung"].strip(),
        )
        matrix[kid] = {typ: int(z[typ]) for typ in szenario_typen}
        meta[kid] = {
            "name": z["kennzahl"].strip(),
            "einheit": z["einheit"].strip(),
            "dimension": z["dimension"].strip(),
            "quelle": z.get("quelle", "").strip(),
        }
    return szenario_typen, kpi_defs, matrix, meta


def aktive_kennzahlen(matrix: dict, typ: str) -> list:
    """Liste der kennzahl_ids, die fuer den gewaehlten Szenario-Typ aktiv (=1) sind."""
    return [kid for kid, spalten in matrix.items() if spalten.get(typ, 0) == 1]


def dimensionen_im_typ(kpi_defs: dict, aktiv_kids: list) -> list:
    """Liste der Dimensionen, die im gewaehlten Typ ueberhaupt vorkommen
    (Reihenfolge stabil nach erstem Auftreten)."""
    gesehen = []
    for kid in aktiv_kids:
        d = kpi_defs[kid].dimension
        if d not in gesehen:
            gesehen.append(d)
    return gesehen
