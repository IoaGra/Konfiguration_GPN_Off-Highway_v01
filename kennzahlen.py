"""
kennzahlen.py
=============
Deterministische Kennzahlen-Formeln und Normalisierungslogik fuer das
MCDA-/Nutzwertanalyse-Entscheidungsmodell zur Konfiguration globaler
Produktionsnetzwerke.

Architekturhinweis
------------------
Dieses Modul enthaelt AUSSCHLIESSLICH deterministische Berechnungen. Es ist
so aufgebaut, dass es vom LLM-Orchestrator (Function Calling) aufgerufen
werden kann, ohne dass der LLM selbst rechnet. Die Funktionen sind rein
(keine Seiteneffekte) und damit gut testbar.

Quellen der Kennzahlen-Definitionen:
  - Gottmann, J. (2019): Produktionscontrolling. Kennzahlensammlung (Kap. 4)
    und Wertstromkennzahlensystem (Kap. 7).
  - Verhaelen, B. et al. (2021): A comprehensive KPI network for the
    performance measurement and management in global production networks.
    Production Engineering 15, 635-650. (Network Performance Indicators, Fig. 6)
  - Schollemann, A. (2025): Strategische Ausrichtung nachhaltiger
    Produktionsnetzwerke. (Oekologische PLIs/NLIs, Abb. 9-50 / 9-52)

Konventionen
------------
- "richtung" eines KPI: "max" (hoeher = besser) oder "min" (niedriger = besser).
- Normalisierung erfolgt relativ (Min-Max) NUR ueber die je Szenario aktiven
  KPIs. Inaktive KPIs (Matrix-Eintrag 0) werden vor der Normalisierung
  entfernt und gehen NICHT in den Nutzwert ein.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Sequence


# ---------------------------------------------------------------------------
# 1) KENNZAHLEN-FORMELN
# ---------------------------------------------------------------------------
# Jede Funktion gibt den Rohwert des KPI zurueck. Division durch Null wird
# defensiv behandelt (Rueckgabe 0.0), damit der Chatbot bei unvollstaendigen
# Nutzereingaben nicht abstuerzt.

def _safe_div(zaehler: float, nenner: float) -> float:
    """Division mit Schutz gegen Division durch Null."""
    return zaehler / nenner if nenner else 0.0


# --- Qualitaet -------------------------------------------------------------

def qualitaetsrate(gutteile: float, gesamtproduktion: float) -> float:
    """Qualitaetsgrad/Qualitaetsrate (%) = Gutteile / Gesamtproduktion * 100.
    Quelle: Gottmann 2019 (Abb. 4.36); Verhaelen et al. 2021 (quality rate)."""
    return _safe_div(gutteile, gesamtproduktion) * 100.0


def reklamationsrate(reklamierte_auftraege: float, gesamtauftraege: float) -> float:
    """Reklamationsrate (%) = reklamierte Auftraege / Gesamtauftraege * 100.
    Quelle: Verhaelen et al. 2021 (complaints rate)."""
    return _safe_div(reklamierte_auftraege, gesamtauftraege) * 100.0


def ausschussquote(ausschuss_stueck: float, gesamtproduktion: float) -> float:
    """Ausschussquote (%) = Ausschuss / Gesamtproduktion * 100.
    Quelle: Gottmann 2019 (Kap. 4.4)."""
    return _safe_div(ausschuss_stueck, gesamtproduktion) * 100.0


def liefertreue_rate(puenktliche_lieferungen: float, gesamtlieferungen: float) -> float:
    """Liefertreue-/OTD-Rate (%) = puenktliche Lieferungen / gesamt * 100.
    Quelle: Verhaelen et al. 2021 (on-time-delivery); Gottmann 2019 (Liefertermintreue)."""
    return _safe_div(puenktliche_lieferungen, gesamtlieferungen) * 100.0


# --- Zeit ------------------------------------------------------------------

def durchlaufzeit(bearbeitungszeit: float, liegezeit: float, transportzeit: float) -> float:
    """Durchlaufzeit (Zeit) = Bearbeitungszeit + Liegezeit + Transportzeit.
    Quelle: Gottmann 2019 (Wertstrommethode); Verhaelen et al. 2021 (throughput time)."""
    return bearbeitungszeit + liegezeit + transportzeit


def durchlaufzeitabweichung(ist_dlz: float, soll_dlz: float) -> float:
    """Durchlaufzeitabweichung (Zeit) = |Ist-DLZ - Soll-DLZ|.
    Quelle: Verhaelen et al. 2021 (throughput time deviation)."""
    return abs(ist_dlz - soll_dlz)


def termintreue(puenktliche_auftraege: float, gesamtauftraege: float) -> float:
    """Termintreue (%) = puenktliche Auftraege / Gesamtauftraege * 100.
    Quelle: Gottmann 2019 (Abb. 4.3); Verhaelen et al. 2021."""
    return _safe_div(puenktliche_auftraege, gesamtauftraege) * 100.0


def wiederbeschaffungszeit(bestellzeit: float, bereitstellzeit: float,
                           transportzeit: float) -> float:
    """Wiederbeschaffungszeit (Zeit) = Bestell- + Bereitstell- + Transportzeit.
    Quelle: Gottmann 2019 (Abb. 4.6)."""
    return bestellzeit + bereitstellzeit + transportzeit


# --- Flexibilitaet ---------------------------------------------------------

def produktflexibilitaet(anzahl_varianten: float, max_varianten: float) -> float:
    """Produktflexibilitaet (%) = herstellbare Varianten / max. Varianten * 100.
    Quelle: Verhaelen et al. 2021 (product flexibility)."""
    return _safe_div(anzahl_varianten, max_varianten) * 100.0


def variantenflexibilitaet(varianten_ohne_mehraufwand: float,
                           gesamt_varianten: float) -> float:
    """Varianten-/Losgroessenflexibilitaet (%).
    Anteil der Varianten, die ohne wesentlichen Mehraufwand gefertigt werden.
    Quelle: Gottmann 2019 (Kap. 7.3.6); Verhaelen et al. 2021 (batch size)."""
    return _safe_div(varianten_ohne_mehraufwand, gesamt_varianten) * 100.0


def reaktionszeit_lieferanten(summe_reaktionszeiten: float, anzahl_anfragen: float) -> float:
    """Reaktionszeit Lieferanten (Zeit) = Summe Reaktionszeiten / Anzahl Anfragen.
    Quelle: Gottmann 2019 (Abb. 4.7)."""
    return _safe_div(summe_reaktionszeiten, anzahl_anfragen)


def kapazitaetsauslastung(genutzte_kapazitaet: float, verfuegbare_kapazitaet: float) -> float:
    """Kapazitaetsauslastung (%) = genutzte / verfuegbare Kapazitaet * 100.
    Hinweis: Freie Kapazitaet = 100 - Auslastung dient als Flexibilitaetsmass.
    Quelle: Gottmann 2019 (Kap. 4.2); Verhaelen et al. 2021 (capacity utilization)."""
    return _safe_div(genutzte_kapazitaet, verfuegbare_kapazitaet) * 100.0


# --- Effizienz -------------------------------------------------------------

def produktivitaet(output_menge: float, eingesetzte_zeit: float) -> float:
    """Produktivitaet (Stueck/h) = Output-Menge / eingesetzte Zeit.
    Quelle: Gottmann 2019 (Kap. 4.2); Verhaelen et al. 2021 (productivity)."""
    return _safe_div(output_menge, eingesetzte_zeit)


def produktstueckkosten(gesamtkosten: float, produzierte_menge: float) -> float:
    """Produktstueckkosten (Geldeinheit) = Gesamtkosten / produzierte Menge.
    Quelle: Verhaelen et al. 2021 (product unit cost)."""
    return _safe_div(gesamtkosten, produzierte_menge)


def materialbestand(bestandswert: float) -> float:
    """Materialbestand (Geldeinheit) = Bestandswert (direkt als Eingabe).
    Quelle: Verhaelen et al. 2021 (material stock)."""
    return bestandswert


def oee(verfuegbarkeit: float, leistungsgrad: float, qualitaetsgrad: float) -> float:
    """OEE (%) = Verfuegbarkeit * Leistungsgrad * Qualitaetsgrad.
    Eingaben jeweils als Anteil 0..1; Rueckgabe in %.
    Quelle: Gottmann 2019 (Kap. 4.2)."""
    return verfuegbarkeit * leistungsgrad * qualitaetsgrad * 100.0


# --- Oekologische Nachhaltigkeit -------------------------------------------

def transportemissionen(distanz_km: float, transportmenge_t: float,
                        emissionsfaktor: float) -> float:
    """Transportemissionen (t CO2) = Distanz * Menge * Emissionsfaktor.
    Emissionsfaktor in t CO2 / (t * km).
    Quelle: Schollemann 2025 (NLI Transportemissionen, Abb. 9-52)."""
    return distanz_km * transportmenge_t * emissionsfaktor


def rate_erneuerbare_energien(erneuerbare_kwh: float, gesamt_kwh: float) -> float:
    """Rate erneuerbarer Energien (%) = erneuerbare kWh / gesamt kWh * 100.
    Quelle: Schollemann 2025 (NLI Rate an erneuerbaren Energien im Netzwerk)."""
    return _safe_div(erneuerbare_kwh, gesamt_kwh) * 100.0


def recyclingmaterial_anteil(recyclingmaterial: float, gesamtmaterial: float) -> float:
    """Recyclingmaterial-Anteil (%) = Recyclingmaterial / Gesamtmaterial * 100.
    Quelle: Schollemann 2025 (NLI Anteil des Recyclingmaterials im Netzwerk)."""
    return _safe_div(recyclingmaterial, gesamtmaterial) * 100.0


def flaecheninanspruchnahme(flaeche_km2: float) -> float:
    """Flaecheninanspruchnahme (km2) = beanspruchte Flaeche (direkt als Eingabe).
    Quelle: Schollemann 2025 (PLI Flaecheninanspruchnahme / NLI)."""
    return flaeche_km2


# ---------------------------------------------------------------------------
# 2) NORMALISIERUNG (Min-Max, nur ueber aktive KPIs)
# ---------------------------------------------------------------------------

def normalisiere_kpi(werte: Sequence[float], richtung: str) -> List[float]:
    """Relative Min-Max-Normalisierung eines einzelnen KPI ueber alle Szenarien.

    werte    : Rohwerte des KPI je Szenario (gleiche Reihenfolge).
    richtung : "max" -> hoeher ist besser; "min" -> niedriger ist besser.

    Rueckgabe: Liste normierter Werte in [0, 1].
    Bei identischen Werten (max == min) wird neutral 1.0 zurueckgegeben,
    damit ein nicht differenzierender KPI niemanden benachteiligt.
    """
    if not werte:
        return []
    v_min, v_max = min(werte), max(werte)
    spannweite = v_max - v_min
    if spannweite == 0:
        return [1.0 for _ in werte]
    if richtung == "max":
        return [(v - v_min) / spannweite for v in werte]
    elif richtung == "min":
        return [(v_max - v) / spannweite for v in werte]
    else:
        raise ValueError(f"Unbekannte Richtung: {richtung!r} (erwartet 'max' oder 'min')")


# ---------------------------------------------------------------------------
# 3) NUTZWERT-BERECHNUNG
# ---------------------------------------------------------------------------

@dataclass
class KpiDefinition:
    """Metadaten eines KPI aus der Szenario-Kennzahl-Matrix."""
    kennzahl_id: str
    dimension: str
    richtung: str          # "max" oder "min"


def renormiere_gewichte(dimension_gewichte: Dict[str, float]) -> Dict[str, float]:
    """Renormiert Dimensionsgewichte auf Summe 1.0 (Auto-Renormalisierung)."""
    summe = sum(dimension_gewichte.values())
    if summe == 0:
        raise ValueError("Summe der Dimensionsgewichte ist 0.")
    return {dim: g / summe for dim, g in dimension_gewichte.items()}


def berechne_nutzwerte(
    rohwerte: Dict[str, Dict[str, float]],
    aktiv: Dict[str, Dict[str, int]],
    kpi_defs: Dict[str, KpiDefinition],
    dimension_gewichte: Dict[str, float],
) -> Dict[str, float]:
    """Berechnet den Nutzwert je Szenario.

    Parameter
    ---------
    rohwerte : {szenario: {kennzahl_id: rohwert}}
        Vom Nutzer ueber den Chatbot eingegebene (oder berechnete) KPI-Rohwerte.
    aktiv : {szenario: {kennzahl_id: 0|1}}
        Aktiv/Inaktiv-Kodierung aus der Szenario-Kennzahl-Matrix.
    kpi_defs : {kennzahl_id: KpiDefinition}
        Metadaten (Dimension, Richtung) je KPI.
    dimension_gewichte : {dimension: gewicht}
        Gewichte der Leistungsdimensionen (werden auto-renormiert).

    Vorgehen
    --------
    1) Je KPI wird ueber ALLE Szenarien normalisiert, in denen er aktiv ist.
       Inaktive Szenarien werden bei diesem KPI uebersprungen.
    2) Je Szenario wird pro Dimension der Mittelwert der normierten aktiven
       KPIs gebildet (KPIs sind innerhalb einer Dimension gleichgewichtet).
       Sind in einer Dimension fuer ein Szenario keine KPIs aktiv, wird diese
       Dimension fuer dieses Szenario aus der Gewichtung herausgenommen und
       die uebrigen Dimensionsgewichte renormiert (faire Behandlung).
    3) Der Nutzwert ist die gewichtete Summe der Dimensions-Scores.

    Rueckgabe
    ---------
    {szenario: nutzwert} mit Nutzwert in [0, 1].
    """
    szenarien = list(rohwerte.keys())

    # --- Schritt 1: Normalisierung je KPI nur ueber aktive Szenarien --------
    normiert: Dict[str, Dict[str, float]] = {s: {} for s in szenarien}
    for kid, kdef in kpi_defs.items():
        aktive_szen = [s for s in szenarien if aktiv.get(s, {}).get(kid, 0) == 1]
        if not aktive_szen:
            continue
        werte = [rohwerte[s].get(kid, 0.0) for s in aktive_szen]
        norm = normalisiere_kpi(werte, kdef.richtung)
        for s, nv in zip(aktive_szen, norm):
            normiert[s][kid] = nv

    # --- Schritt 2 & 3: Dimensions-Scores und gewichteter Nutzwert ----------
    nutzwerte: Dict[str, float] = {}
    for s in szenarien:
        # Dimensions-Score = Mittelwert der normierten aktiven KPIs der Dimension
        dim_scores: Dict[str, float] = {}
        for dim in dimension_gewichte:
            kids = [kid for kid, kdef in kpi_defs.items()
                    if kdef.dimension == dim and kid in normiert[s]]
            if kids:
                dim_scores[dim] = sum(normiert[s][kid] for kid in kids) / len(kids)

        if not dim_scores:
            nutzwerte[s] = 0.0
            continue

        # Gewichte auf die tatsaechlich vorhandenen Dimensionen renormieren
        aktive_gewichte = {d: dimension_gewichte[d] for d in dim_scores}
        aktive_gewichte = renormiere_gewichte(aktive_gewichte)

        nutzwerte[s] = sum(dim_scores[d] * aktive_gewichte[d] for d in dim_scores)

    return nutzwerte
