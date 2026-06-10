"""
daten.py  (V6)
==============
Liest die Datei 'daten.xlsx' mit der vollstaendigen Datengrundlage:

  Leistungsdimension | Kennzahl | Einheit | Zielwert | Grenzwert | <Option 1> | <Option 2> | ...

Die Optionen (Spalten ab der sechsten) sind die im Szenario betrachtbaren
Standorte/Auspraegungen, z.B. Warschau, Peking, Koeln, Budapest,
'keine Aenderung'. Fehlende Werte sind mit '/' markiert und muessen vom
Nutzer abgefragt werden.

Diese Werte sind als Beispieldaten zu verstehen, die der Chatbot in der
Praxis aus Unternehmenssystemen beziehen wuerde.
"""

import os
from openpyxl import load_workbook

FEHLEND = "/"   # Markierung fuer fehlende Werte in daten.xlsx


def lade_daten(pfad: str = "daten.xlsx"):
    """Liest daten.xlsx und gibt zurueck:

    kpis      : {kennzahl: {dimension, einheit, zielwert, grenzwert}}
                (Reihenfolge wie in der Datei; Kennzahl-Name = Schluessel)
    optionen  : Liste der Options-Spalten (Standorte/Auspraegungen)
    werte     : {option: {kennzahl: float}}   nur vorhandene Werte
    fehlend   : {option: [kennzahl, ...]}     mit '/' markierte Luecken
    """
    if not os.path.exists(pfad):
        return {}, [], {}, {}

    wb = load_workbook(pfad, data_only=True)
    ws = wb.active
    zeilen = list(ws.iter_rows(values_only=True))
    if not zeilen:
        return {}, [], {}, {}

    kopf = [str(z).strip() if z is not None else "" for z in zeilen[0]]
    # Spalten: 0=Dimension, 1=Kennzahl, 2=Einheit, 3=Zielwert, 4=Grenzwert, 5+=Optionen
    optionen = [kopf[i] for i in range(5, len(kopf)) if kopf[i]]

    kpis, werte, fehlend = {}, {o: {} for o in optionen}, {o: [] for o in optionen}
    for z in zeilen[1:]:
        if not z or z[1] is None:
            continue
        kennzahl = str(z[1]).strip()
        kpis[kennzahl] = {
            "dimension": str(z[0]).strip(),
            "einheit": str(z[2]).strip() if z[2] is not None else "",
            "zielwert": float(z[3]),
            "grenzwert": float(z[4]),
        }
        for i, opt in enumerate(optionen):
            zelle = z[5 + i] if 5 + i < len(z) else None
            if zelle is None or (isinstance(zelle, str) and zelle.strip() == FEHLEND):
                fehlend[opt].append(kennzahl)
            else:
                try:
                    werte[opt][kennzahl] = float(zelle)
                except (TypeError, ValueError):
                    fehlend[opt].append(kennzahl)

    return kpis, optionen, werte, fehlend


def dimensionen_aus_kpis(kpis: dict) -> list:
    """Dimensionen in stabiler Reihenfolge des ersten Auftretens."""
    gesehen = []
    for info in kpis.values():
        if info["dimension"] not in gesehen:
            gesehen.append(info["dimension"])
    return gesehen
