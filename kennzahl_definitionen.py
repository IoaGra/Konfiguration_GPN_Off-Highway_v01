"""
kennzahl_definitionen.py
========================
Zentrale Definition aller Kennzahlen. Matrix, Excel, Berechnung und App
greifen auf diese eine Quelle zu, damit alles konsistent bleibt.

Felder je Kennzahl:
  dimension   : technischer Dimensionsname (ohne Umlaute)
  name        : Anzeigename (mit Umlauten erlaubt)
  einheit     : Anzeige-Einheit
  richtung    : 'max' (hoeher=besser) | 'min' (niedriger=besser)
  erfassung   : woher der Wert kommt
                'excel'   -> liegt in den System-Beispieldaten (beispieldaten.xlsx)
                'eingabe' -> der Nutzer gibt den Wert selbst ein
                'oee'     -> wird aus drei Faktoren berechnet (Nutzereingabe)
                'fiktiv'  -> der Chatbot setzt einen plausiblen Wert ein
  zielwert    : Bezugswert fuer die Zielwert-Normierung
                (Nutzen: wert/ziel; Kosten: ziel/wert; je gedeckelt auf 1)

Die ZIELWERTE sind plausibel gesetzt und von dir zu pruefen/anzupassen.
"""

# kennzahl_id -> (dimension, name, einheit, richtung, erfassung, zielwert)
KENNZAHLEN = {
    # --- Effizienz ---
    "kapazitaetsauslastung":   ("Effizienz", "Kapazitätsauslastung", "%", "max", "excel", 95),
    "fertigungskosten":        ("Effizienz", "Fertigungskosten", "EUR/Stk", "min", "excel", 8.0),
    "materialbestand":         ("Effizienz", "Materialbestand", "EUR", "min", "excel", 400000),
    "oee":                     ("Effizienz", "OEE", "%", "max", "oee", 90),
    # --- Qualitaet ---
    "qualitaetsrate":          ("Qualitaet", "Qualitätsrate", "%", "max", "excel", 100),
    "reklamationsrate":        ("Qualitaet", "Reklamationsrate", "%", "min", "excel", 0.5),
    "liefertermintreue":       ("Qualitaet", "Liefertermintreue", "%", "max", "excel", 100),
    "ausschussquote":          ("Qualitaet", "Ausschussquote", "%", "min", "eingabe", 1.0),
    "nacharbeitsquote":        ("Qualitaet", "Nacharbeitsquote", "%", "min", "fiktiv", 1.5),
    # --- Zeit ---
    "durchlaufzeit":           ("Zeit", "Durchlaufzeit", "Tage", "min", "excel", 8.0),
    "durchlaufzeitabweichung": ("Zeit", "Durchlaufzeitabweichung", "Tage", "min", "fiktiv", 1.0),
    "transportzeit":           ("Zeit", "Transportzeit", "Tage", "min", "fiktiv", 2.0),
    # --- Flexibilitaet ---
    "produktflexibilitaet":    ("Flexibilitaet", "Produktflexibilität", "%", "max", "fiktiv", 100),
    "losgroesse":              ("Flexibilitaet", "Losgröße", "Stk", "min", "fiktiv", 300),
    "volumenflexibilitaet":    ("Flexibilitaet", "Volumenflexibilität", "%", "max", "fiktiv", 100),
    "variantenflexibilitaet":  ("Flexibilitaet", "Variantenflexibilität", "%", "max", "fiktiv", 100),
    "transportvolumenflexibilitaet": ("Flexibilitaet", "Transportvolumenflexibilität", "%", "max", "fiktiv", 100),
    # --- Oekologische Nachhaltigkeit ---
    "co2_emissionen":          ("Oekologische Nachhaltigkeit", "CO2-Emissionen", "kg/Jahr", "min", "eingabe", 100000),
    "anteil_erneuerbare_energie": ("Oekologische Nachhaltigkeit", "Anteil erneuerbarer Energie", "%", "max", "excel", 100),
}

# Reihenfolge der Dimensionen (fuer Anzeige)
DIMENSIONEN_REIHENFOLGE = ["Effizienz", "Qualitaet", "Zeit", "Flexibilitaet",
                           "Oekologische Nachhaltigkeit"]


def feld(kid, index):
    return KENNZAHLEN[kid][index]

def dimension(kid):  return KENNZAHLEN[kid][0]
def name(kid):       return KENNZAHLEN[kid][1]
def einheit(kid):    return KENNZAHLEN[kid][2]
def richtung(kid):   return KENNZAHLEN[kid][3]
def erfassung(kid):  return KENNZAHLEN[kid][4]
def zielwert(kid):   return KENNZAHLEN[kid][5]
