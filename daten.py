"""
daten.py
========
Liest die hinterlegte Excel-Beispieldatei mit FERTIGEN Kennzahlenwerten.

Erwartetes Format (eine Tabelle):
  kennzahl_id | Kennzahl | Einheit | <Standort_A> | <Standort_B> | ...

Die erste Spalte 'kennzahl_id' muss exakt den IDs aus der Matrix und aus
kennzahlen.py entsprechen. Jede weitere (vierte und folgende) Spalte ist ein
Szenario/Standort mit dem bereits fertig berechneten Kennzahlenwert.

In der Praxis wuerden diese Werte aus einem Unternehmenssystem kommen; hier
dienen sie als vereinfachte Beispieldaten.
"""

import os

try:
    from openpyxl import load_workbook
    _OPENPYXL = True
except ImportError:
    _OPENPYXL = False


def lade_beispieldaten(pfad: str = "beispieldaten.xlsx"):
    """Liest die Excel und gibt zwei Strukturen zurueck:

    werte        : {standort: {kennzahl_id: wert}}
    standorte    : Liste der Spaltennamen (Szenarien/Standorte)

    Gibt ({}, []) zurueck, wenn keine Datei vorhanden ist.
    """
    if not os.path.exists(pfad) or not _OPENPYXL:
        return {}, []

    wb = load_workbook(pfad, data_only=True)
    ws = wb.active

    zeilen = list(ws.iter_rows(values_only=True))
    if not zeilen:
        return {}, []

    kopf = [str(z).strip() if z is not None else "" for z in zeilen[0]]
    # Spalten ab Index 3 (vierte Spalte) sind Standorte
    if len(kopf) < 4:
        return {}, []
    standort_spalten = list(range(3, len(kopf)))
    standorte = [kopf[i] for i in standort_spalten]

    werte = {s: {} for s in standorte}
    for zeile in zeilen[1:]:
        if not zeile or zeile[0] is None:
            continue
        kid = str(zeile[0]).strip()
        if not kid or kid.lower().startswith("hinweis"):
            continue
        for idx, s in zip(standort_spalten, standorte):
            wert = zeile[idx] if idx < len(zeile) else None
            if isinstance(wert, (int, float)):
                werte[s][kid] = float(wert)

    return werte, standorte


def verfuegbare_kennzahlen(werte: dict, standort: str) -> dict:
    """Gibt {kennzahl_id: wert} fuer einen Standort zurueck (nur vorhandene)."""
    return dict(werte.get(standort, {}))
