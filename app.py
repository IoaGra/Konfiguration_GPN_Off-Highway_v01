# =============================================================
#  HAUPTANWENDUNG (Streamlit) - Version 4
# =============================================================
#  Entscheidungsunterstuetzung zur Konfiguration globaler
#  Produktionsnetzwerke.
#
#  Neu gegenueber V3:
#   - Freie Navigation: ueber die Fortschrittsanzeige links kann
#     zu jeder Phase gesprungen werden (Daten bleiben erhalten).
#   - Phase 2 zeigt zusaetzlich Erklaerungen zu den Dimensionen.
#   - Datenabfrage mit Herkunft je Wert: 'system' (Excel),
#     'nutzer' (Eingabe) oder 'schaetzung'. Die Herkunft wird
#     transparent gemacht (Datenqualitaetsfaktor noch NICHT in
#     der Berechnung aktiv, aber vorbereitet).
#   - Phase 4 zeigt NUR eine Datenuebersicht (Wert, Einheit,
#     Herkunft) - KEINE Nutzwerte.
#   - Berechnung + Ergebnis erst in Phase 5.
#
#  Modell: Sonnet 4.6.
# =============================================================

import os
import json
import base64
import streamlit as st
import anthropic

from kennzahlen import berechne_nutzwerte, KpiDefinition
from matrix import (lade_matrix, aktive_kennzahlen, dimensionen_im_typ,
                    SZENARIO_TYP_LABELS)
from szenarien import SZENARIO_BESCHREIBUNGEN
from dimensionen import dim_beschreibung
from daten import lade_beispieldaten
from anzeige import dim_anzeige
from phasen import PHASEN, ANZAHL_PHASEN, einfuehrungstext
from pdf_export import erstelle_ergebnis_pdf

# -------------------------------------------------------------
#  Grundeinstellungen
# -------------------------------------------------------------
MODELL = "claude-sonnet-4-6"
MAX_TOKENS = 1500
EXCEL_PFAD = "beispieldaten.xlsx"

# Herkunfts-Kennzeichnung (Transparenz). Der Zahlenwert ist der spaetere
# Datenqualitaetsfaktor (Variante A) - aktuell nur zur Anzeige, NICHT in der
# Berechnung verwendet.
HERKUNFT_LABEL = {
    "system": "aus System (Excel)",
    "nutzer": "Nutzereingabe",
    "schaetzung": "Schätzung",
}
HERKUNFT_FAKTOR = {"system": 0.7, "nutzer": 1.0, "schaetzung": 0.3}

st.set_page_config(page_title="Entscheidungsmodell Produktionsnetzwerke",
                   page_icon="🏭", layout="wide")

# -------------------------------------------------------------
#  API-Schluessel
# -------------------------------------------------------------
try:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    st.error("Kein API-Schluessel gefunden. Bitte in den App-Einstellungen "
             "unter 'Secrets' den Eintrag ANTHROPIC_API_KEY hinterlegen.")
    st.stop()

# -------------------------------------------------------------
#  Statische Daten (gecached)
# -------------------------------------------------------------
@st.cache_data
def _lade_matrix():
    return lade_matrix("szenario_kennzahl_matrix.csv")

@st.cache_data
def _lade_excel():
    return lade_beispieldaten(EXCEL_PFAD)

SZENARIO_TYPEN, KPI_DEFS, MATRIX, META = _lade_matrix()
EXCEL_WERTE, EXCEL_STANDORTE = _lade_excel()

# =============================================================
#  HILFSFUNKTIONEN
# =============================================================

def kennzahlen_nach_dimension(typ):
    aktiv = aktive_kennzahlen(MATRIX, typ)
    gruppen = {}
    for kid in aktiv:
        d = KPI_DEFS[kid].dimension
        gruppen.setdefault(d, []).append(
            (kid, META[kid]["name"], META[kid]["einheit"], KPI_DEFS[kid].richtung))
    return gruppen


def rechne(rohwerte, gewichte, typ):
    """Deterministische Berechnung. rohwerte: {szenario: {kid: wert}}."""
    aktiv_kids = aktive_kennzahlen(MATRIX, typ)
    szenarien = list(rohwerte.keys())
    aktiv = {s: {kid: (1 if kid in aktiv_kids else 0) for kid in KPI_DEFS}
             for s in szenarien}
    kpi_defs_aktiv = {kid: KPI_DEFS[kid] for kid in aktiv_kids}
    nutzwerte = berechne_nutzwerte(rohwerte, aktiv, kpi_defs_aktiv, gewichte)
    rangliste = sorted(nutzwerte.items(), key=lambda kv: kv[1], reverse=True)
    raenge = {s: i + 1 for i, (s, _) in enumerate(rangliste)}
    return {
        "nutzwerte": {s: round(v, 4) for s, v in nutzwerte.items()},
        "raenge": raenge,
        "empfehlung": rangliste[0][0],
        "gewichte": {d: round(w, 4) for d, w in gewichte.items()},
    }


def nur_rohwerte(erfasst):
    """Extrahiert {szenario: {kid: wert}} aus der Erfassung mit Herkunft
    ({szenario: {kid: {'wert':..., 'herkunft':...}}})."""
    return {s: {kid: eintrag["wert"] for kid, eintrag in kvs.items()}
            for s, kvs in erfasst.items()}


def slider_geaendert(geaendert, dims):
    neu = st.session_state[f"w_{geaendert}"]
    andere = [d for d in dims if d != geaendert]
    if not andere:
        return
    rest_alt = sum(st.session_state[f"w_{d}"] for d in andere)
    rest_neu = 100 - neu
    if rest_alt == 0:
        for d in andere:
            st.session_state[f"w_{d}"] = rest_neu / len(andere)
    else:
        faktor = rest_neu / rest_alt
        verteilt = 0
        for d in andere[:-1]:
            st.session_state[f"w_{d}"] = round(st.session_state[f"w_{d}"] * faktor)
            verteilt += st.session_state[f"w_{d}"]
        st.session_state[f"w_{andere[-1]}"] = rest_neu - verteilt
    for d in dims:
        st.session_state.gewichte[d] = st.session_state[f"w_{d}"] / 100.0


def zeige_gewichts_slider(dims):
    for d in dims:
        if f"w_{d}" not in st.session_state:
            st.session_state[f"w_{d}"] = round(st.session_state.gewichte[d] * 100)
    for d in dims:
        st.slider(dim_anzeige(d), min_value=0, max_value=100, key=f"w_{d}",
                  on_change=slider_geaendert, args=(d, dims))
    summe = sum(st.session_state[f"w_{d}"] for d in dims)
    st.write(f"**Summe:** {summe} %")
    return summe


def ordne_szenario_typ_zu(nutzertext):
    typen_liste = "\n".join(f"- {t}: {SZENARIO_TYP_LABELS.get(t, t)}"
                            for t in SZENARIO_TYPEN)
    prompt = (
        "Ordne die folgende Nutzeraussage genau EINEM der Szenario-Typen zu. "
        "Antworte NUR mit dem technischen Schluessel (z.B. 'verlagerung'), "
        "ohne weiteren Text. Wenn unklar, antworte 'unklar'.\n\n"
        f"Verfuegbare Typen:\n{typen_liste}\n\n"
        f"Nutzeraussage: \"{nutzertext}\"")
    antwort = client.messages.create(
        model=MODELL, max_tokens=20,
        messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in antwort.content
                   if getattr(b, "type", None) == "text").strip().lower()
    for t in SZENARIO_TYPEN:
        if t in text:
            return t
    return None


# ---- Dialog (Phase 4 Datenerfassung) ----
def baue_system_prompt():
    typ = st.session_state.typ
    aktiv_kids = aktive_kennzahlen(MATRIX, typ)
    kennzahl_liste = ""
    for kid in aktiv_kids:
        m = META[kid]
        kennzahl_liste += (f"- {kid}: {m['name']} "
                           f"(Dimension {m['dimension']}, Einheit {m['einheit']}, "
                           f"Richtung {KPI_DEFS[kid].richtung})\n")
    label = SZENARIO_TYP_LABELS.get(typ, typ)

    excel_hinweis = ""
    if EXCEL_WERTE:
        zeilen = []
        for standort, kvs in EXCEL_WERTE.items():
            relevante = {k: v for k, v in kvs.items() if k in aktiv_kids}
            if relevante:
                zeilen.append(f"{standort}: " +
                              ", ".join(f"{k}={v}" for k, v in relevante.items()))
        if zeilen:
            excel_hinweis = (
                "\nFolgende Werte liegen als System-Daten (Excel) vor. Nutze sie "
                "und kennzeichne sie als Herkunft 'system'. Frage sie NICHT erneut "
                "ab:\n" + "\n".join(zeilen) + "\n")

    return f"""Du bist ein Assistent zur Entscheidungsunterstuetzung bei der \
Konfiguration globaler Produktionsnetzwerke. Wir sind in Phase 4 (Datenabfrage).

Szenario-Typ: '{label}'.

Fuer diesen Typ sind ausschliesslich folgende Kennzahlen relevant:
{kennzahl_liste}{excel_hinweis}
Deine Aufgabe in Phase 4:
1. Erfasse fuer MINDESTENS ZWEI Konfigurationen alle oben gelisteten Kennzahlen.
2. Werte aus den System-Daten (Excel) uebernimmst du mit Herkunft 'system'. \
Fehlende Werte fragst du beim Nutzer ab (Herkunft 'nutzer'). Wenn der Nutzer \
einen Wert nicht kennt und du ihn schaetzen sollst, kennzeichne ihn als \
'schaetzung'.
3. Mache bei jeder Antwort transparent, welche Werte aus dem System stammen \
und welche der Nutzer eingegeben hat.
4. Wenn fuer alle Konfigurationen alle Kennzahlen erfasst sind, rufe das \
Werkzeug 'speichere_daten' auf (NICHT rechnen - die Berechnung erfolgt spaeter \
in Phase 5).

Antworte auf Deutsch, sachlich und knapp. Wenige Fragen gleichzeitig."""


def tool_definitionen():
    return [{
        "name": "speichere_daten",
        "description": (
            "Speichert die erfassten Kennzahlenwerte je Szenario inklusive "
            "Herkunft. Aufrufen, sobald alle Werte aller Szenarien vorliegen. "
            "NICHT rechnen - die Berechnung erfolgt separat in Phase 5."),
        "input_schema": {
            "type": "object",
            "properties": {
                "daten": {
                    "type": "object",
                    "description": (
                        "{Szenarioname: {kennzahl_id: {\"wert\": Zahl, "
                        "\"herkunft\": \"system\"|\"nutzer\"|\"schaetzung\"}}}"),
                }
            },
            "required": ["daten"],
        },
    }]


def fuehre_dialog_runde():
    while True:
        antwort = client.messages.create(
            model=MODELL, max_tokens=MAX_TOKENS,
            system=baue_system_prompt(),
            tools=tool_definitionen(),
            messages=st.session_state.messages)
        st.session_state.messages.append(
            {"role": "assistant", "content": antwort.content})
        tool_aufrufe = [b for b in antwort.content
                        if getattr(b, "type", None) == "tool_use"]
        if not tool_aufrufe:
            return
        ergebnisse = []
        for aufruf in tool_aufrufe:
            if aufruf.name == "speichere_daten":
                daten = aufruf.input["daten"]
                # Normalisieren: sicherstellen, dass jede Zelle wert+herkunft hat
                erfasst = {}
                for s, kvs in daten.items():
                    erfasst[s] = {}
                    for kid, eintrag in kvs.items():
                        if isinstance(eintrag, dict):
                            wert = eintrag.get("wert")
                            herk = eintrag.get("herkunft", "nutzer")
                        else:
                            wert, herk = eintrag, "nutzer"
                        if wert is not None:
                            erfasst[s][kid] = {"wert": float(wert),
                                               "herkunft": herk}
                st.session_state.erfasste_daten = erfasst
                ergebnisse.append({
                    "type": "tool_result", "tool_use_id": aufruf.id,
                    "content": "Daten gespeichert. Bitte dem Nutzer kurz "
                               "bestaetigen und auf Phase 5 verweisen."})
        st.session_state.messages.append({"role": "user", "content": ergebnisse})


def _block_attr(b, name):
    return b.get(name) if isinstance(b, dict) else getattr(b, name, None)


def zeige_verlauf():
    for m in st.session_state.messages:
        if m["role"] == "user":
            if isinstance(m["content"], str):
                with st.chat_message("user"):
                    st.markdown(m["content"])
        elif m["role"] == "assistant" and isinstance(m["content"], list):
            for b in m["content"]:
                if _block_attr(b, "type") == "text":
                    with st.chat_message("assistant"):
                        st.markdown(_block_attr(b, "text"))


def letzter_bot_text():
    for m in reversed(st.session_state.messages):
        if m["role"] == "assistant" and isinstance(m["content"], list):
            texte = [_block_attr(b, "text") for b in m["content"]
                     if _block_attr(b, "type") == "text"]
            if texte:
                return "\n".join(t for t in texte if t)
    return ""


def gehe_zu_phase(p):
    st.session_state.phase = p


# =============================================================
#  Sitzungsspeicher
# =============================================================
for key, default in [("phase", 1), ("typ", None), ("messages", []),
                     ("gewichte", {}), ("dims", []),
                     ("erfasste_daten", None), ("letztes_ergebnis", None),
                     ("einfuehrung_gezeigt", False),
                     ("phase4_gestartet", False), ("phase7_gezeigt", False)]:
    if key not in st.session_state:
        st.session_state[key] = default

# =============================================================
#  KOPF + NAVIGIERBARE FORTSCHRITTSANZEIGE
# =============================================================
st.title("🏭 Entscheidungsmodell: globale Produktionsnetzwerke")

with st.sidebar:
    st.subheader("Phasen")
    st.caption("Du kannst zu bereits erreichten Phasen zurückspringen.")
    for i in range(1, ANZAHL_PHASEN + 1):
        ist_aktuell = (i == st.session_state.phase)
        # Springen nur erlaubt, wenn ein Typ gewaehlt ist (ausser Phase 1)
        erlaubt = (i == 1) or (st.session_state.typ is not None)
        marker = "▶️" if ist_aktuell else ("✅" if i < st.session_state.phase else "▫️")
        label = f"{marker} {PHASEN[i]['titel']}"
        if st.button(label, key=f"nav_{i}", disabled=not erlaubt or ist_aktuell,
                     width="stretch"):
            gehe_zu_phase(i)
            st.rerun()
    st.divider()
    if st.button("🔁 Neue Analyse starten", width="stretch"):
        for k in list(st.session_state.keys()):
            st.session_state.pop(k, None)
        st.rerun()

PHASE = st.session_state.phase

# =============================================================
#  PHASE 1 — Einfuehrung + textliche Szenario-Auswahl
# =============================================================
if PHASE == 1:
    if not st.session_state.einfuehrung_gezeigt:
        st.markdown(einfuehrungstext())
        st.session_state.einfuehrung_gezeigt = True

    st.divider()
    st.subheader("Phase 1: Welche Entscheidung möchtest du untersuchen?")

    if st.session_state.typ is not None:
        st.success(f"Gewählter Szenario-Typ: "
                   f"**{SZENARIO_TYP_LABELS.get(st.session_state.typ)}**")
        if st.button("Weiter zu Phase 2 ▶️"):
            gehe_zu_phase(2)
            st.rerun()

    st.caption("Beschreibe in eigenen Worten, worum es geht — ich ordne es dann "
               "dem passenden Szenario-Typ zu.")
    with st.expander("Welche Szenario-Typen gibt es?"):
        for t in SZENARIO_TYPEN:
            st.markdown(f"- **{SZENARIO_TYP_LABELS.get(t, t)}**: "
                        f"{SZENARIO_BESCHREIBUNGEN.get(t, '')}")

    eingabe = st.chat_input("z. B. 'Wir überlegen, die Produktion an einen "
                            "anderen Standort zu verlagern.'")
    if eingabe:
        with st.spinner("Ordne deine Eingabe einem Szenario-Typ zu …"):
            typ = ordne_szenario_typ_zu(eingabe)
        if typ is None:
            st.warning("Ich konnte das nicht eindeutig zuordnen. Bitte "
                       "formuliere es konkreter oder nenne den Typ direkt.")
        else:
            st.session_state.typ = typ
            aktiv_kids = aktive_kennzahlen(MATRIX, typ)
            dims = dimensionen_im_typ(KPI_DEFS, aktiv_kids)
            st.session_state.dims = dims
            if not st.session_state.gewichte:
                st.session_state.gewichte = {d: 1.0 / len(dims) for d in dims}
            gehe_zu_phase(2)
            st.rerun()
    st.stop()

TYP = st.session_state.typ
DIMS = st.session_state.dims
st.caption(f"Szenario-Typ: **{SZENARIO_TYP_LABELS.get(TYP, TYP)}**")

# =============================================================
#  PHASE 2 — Kennzahlen + Dimensions-Erklaerungen
# =============================================================
if PHASE == 2:
    st.subheader(PHASEN[2]["titel"])
    st.write("Für den gewählten Szenario-Typ sind die folgenden Kennzahlen "
             "relevant, gruppiert nach Leistungsdimension:")
    gruppen = kennzahlen_nach_dimension(TYP)
    for d in DIMS:
        st.markdown(f"### {dim_anzeige(d)}")
        beschr = dim_beschreibung(d)
        if beschr:
            st.caption(beschr)
        for kid, name, einheit, richtung in gruppen.get(d, []):
            pfeil = "↑ höher ist besser" if richtung == "max" else "↓ niedriger ist besser"
            st.markdown(f"- {name} ({einheit}, {pfeil})")
    st.divider()
    if st.button("Weiter zu Phase 3 (Gewichtung) ▶️"):
        gehe_zu_phase(3)
        st.rerun()
    st.stop()

# =============================================================
#  PHASE 3 — Gewichtung
# =============================================================
if PHASE == 3:
    st.subheader(PHASEN[3]["titel"])
    st.write("Lege fest, wie wichtig dir die einzelnen Leistungsdimensionen "
             "sind. Ziehst du einen Regler hoch, passen sich die anderen "
             "automatisch an, sodass die Summe stets 100 % ergibt.")
    zeige_gewichts_slider(DIMS)
    st.divider()
    if st.button("Gewichtung übernehmen und zur Datenabfrage ▶️"):
        gehe_zu_phase(4)
        st.rerun()
    st.stop()

# =============================================================
#  PHASE 4 — Datenabfrage (Chat) + Datenuebersicht (KEINE Nutzwerte)
# =============================================================
if PHASE == 4:
    st.subheader(PHASEN[4]["titel"])
    if EXCEL_WERTE:
        st.caption(f"System-Daten geladen für: {', '.join(EXCEL_STANDORTE)}. "
                   "Fehlende Werte frage ich im Chat ab.")

    if not st.session_state.phase4_gestartet and st.session_state.erfasste_daten is None:
        st.session_state.phase4_gestartet = True
        with st.spinner("Starte die Datenabfrage …"):
            st.session_state.messages.append(
                {"role": "user",
                 "content": "Starte Phase 4. Nutze die System-Daten und frage "
                            "fehlende Kennzahlen ab. Beginne jetzt."})
            fuehre_dialog_runde()
        st.rerun()

    zeige_verlauf()

    # Datenuebersicht, sobald Daten erfasst sind (nur Uebersicht, keine Scores)
    if st.session_state.erfasste_daten is not None:
        st.divider()
        st.markdown("### Übersicht der erfassten Daten")
        st.caption("Diese Werte fließen in die Berechnung ein. Die Herkunft ist "
                   "je Wert ausgewiesen. (Die Nutzwerte werden in Phase 5 berechnet.)")
        erfasst = st.session_state.erfasste_daten
        zeilen = []
        for kid in aktive_kennzahlen(MATRIX, TYP):
            zeile = {"Kennzahl": META[kid]["name"], "Einheit": META[kid]["einheit"]}
            for s in erfasst:
                eintrag = erfasst[s].get(kid)
                if eintrag:
                    zeile[s] = f"{eintrag['wert']} ({HERKUNFT_LABEL.get(eintrag['herkunft'], eintrag['herkunft'])})"
                else:
                    zeile[s] = "—"
            zeilen.append(zeile)
        st.dataframe(zeilen, width="stretch", hide_index=True)

        if st.button("Weiter zu Phase 5 (Berechnung) ▶️"):
            gehe_zu_phase(5)
            st.rerun()
    else:
        eingabe = st.chat_input("Werte eingeben oder Frage stellen …")
        if eingabe:
            st.session_state.messages.append({"role": "user", "content": eingabe})
            with st.spinner("…"):
                fuehre_dialog_runde()
            st.rerun()
    st.stop()

# =============================================================
#  PHASE 5 — Berechnung + Ergebnis (erst hier!)
# =============================================================
if PHASE == 5:
    st.subheader(PHASEN[5]["titel"])
    if st.session_state.erfasste_daten is None:
        st.warning("Es liegen noch keine Daten vor. Bitte zuerst Phase 4 abschließen.")
        st.stop()

    # Berechnung beim Betreten von Phase 5 (immer mit aktueller Gewichtung)
    rohwerte = nur_rohwerte(st.session_state.erfasste_daten)
    st.session_state.letztes_ergebnis = rechne(rohwerte, st.session_state.gewichte, TYP)
    erg = st.session_state.letztes_ergebnis

    st.write("Die Nutzwerte wurden deterministisch berechnet: relative "
             "Min-Max-Normalisierung je Kennzahl, Mittelung je Dimension, "
             "anschließend gewichtete Summe der Dimensionen.")

    st.markdown("**Verwendete Gewichtung:**")
    for d in DIMS:
        st.markdown(f"- {dim_anzeige(d)}: {erg['gewichte'][d]*100:.0f} %")

    st.markdown("**Ergebnis:**")
    st.dataframe(
        [{"Rang": erg["raenge"][s], "Szenario": s, "Nutzwert": nw}
         for s, nw in sorted(erg["nutzwerte"].items(),
                             key=lambda kv: kv[1], reverse=True)],
        width="stretch", hide_index=True)
    st.info(f"Empfehlung nach aktueller Gewichtung: **{erg['empfehlung']}**")

    st.divider()
    if st.button("Weiter zu Phase 6 (Sensitivitätsanalyse) ▶️"):
        gehe_zu_phase(6)
        st.rerun()
    st.stop()

# =============================================================
#  PHASE 6 — Sensitivitaetsanalyse
# =============================================================
if PHASE == 6:
    st.subheader(PHASEN[6]["titel"])
    if st.session_state.erfasste_daten is None:
        st.warning("Es liegen noch keine Daten vor. Bitte zuerst Phase 4 abschließen.")
        st.stop()
    st.write("Verändere die Gewichtung und beobachte, wie sich Rangfolge und "
             "Nutzwerte verschieben. So prüfst du, wie robust die Empfehlung ist.")
    zeige_gewichts_slider(DIMS)

    rohwerte = nur_rohwerte(st.session_state.erfasste_daten)
    if st.button("🔄 Mit aktueller Gewichtung neu berechnen"):
        st.session_state.letztes_ergebnis = rechne(
            rohwerte, st.session_state.gewichte, TYP)
        st.rerun()

    erg = st.session_state.letztes_ergebnis
    if erg:
        st.markdown("**Aktuelles Ergebnis:**")
        st.dataframe(
            [{"Rang": erg["raenge"][s], "Szenario": s, "Nutzwert": nw}
             for s, nw in sorted(erg["nutzwerte"].items(),
                                 key=lambda kv: kv[1], reverse=True)],
            width="stretch", hide_index=True)
        st.info(f"Empfehlung: **{erg['empfehlung']}**")

    st.divider()
    if st.button("Analyse abschließen und Ergebnis erstellen ▶️"):
        gehe_zu_phase(7)
        st.rerun()
    st.stop()

# =============================================================
#  PHASE 7 — Zusammenfassung + PDF
# =============================================================
if PHASE == 7:
    st.subheader(PHASEN[7]["titel"])
    erg = st.session_state.letztes_ergebnis
    if erg is None:
        st.warning("Es liegt noch kein Ergebnis vor. Bitte Phase 5 durchlaufen.")
        st.stop()

    if not st.session_state.phase7_gezeigt:
        st.session_state.phase7_gezeigt = True
        with st.spinner("Erstelle die Zusammenfassung …"):
            st.session_state.messages.append(
                {"role": "user",
                 "content": "Wir sind in Phase 7. Erstelle jetzt die textliche "
                            "Abschluss-Zusammenfassung: Was wird empfohlen? Was "
                            "wurde beruecksichtigt (Szenario-Typ, Kennzahlen, "
                            "Gewichtung)? Was sollte bei weiteren Entscheidungen "
                            "zusaetzlich beachtet werden?"})
            fuehre_dialog_runde()
        st.rerun()

    zeige_verlauf()

    st.divider()
    st.markdown("**Ergebnis als PDF:**")
    zusammenfassung = letzter_bot_text()
    pdf_bytes = erstelle_ergebnis_pdf(
        erg, zusammenfassung, SZENARIO_TYP_LABELS.get(TYP, TYP))
    st.download_button("📄 Ergebnis-PDF herunterladen", data=pdf_bytes,
                       file_name="entscheidungsempfehlung.pdf",
                       mime="application/pdf")
