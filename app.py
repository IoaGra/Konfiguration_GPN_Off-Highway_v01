# =============================================================
#  HAUPTANWENDUNG (Streamlit) - Version 3
# =============================================================
#  Entscheidungsunterstuetzung zur Konfiguration globaler
#  Produktionsnetzwerke.
#
#  Ablauf in 7 STRIKTEN Phasen (jede muss abgeschlossen sein,
#  bevor die naechste freigeschaltet wird):
#    1 Auswahl des Szenarios (textliche Abfrage, kein Dropdown)
#    2 Anzeige der relevanten Kennzahlen (nach Dimension)
#    3 Gewichtung (Slider mit Auto-Ausgleich, Summe 100 %)
#    4 Datenabfrage (Excel-Beispieldaten + Nutzereingabe)
#    5 Berechnung der Scores (transparent, deterministisch)
#    6 Sensitivitaetsanalyse (gleiche Slider, variieren)
#    7 Ergebnis + Zusammenfassung + PDF-Download
#
#  Modell: Sonnet 4.6 (guenstiger als Opus, ausreichend).
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
from daten import lade_beispieldaten
from anzeige import dim_anzeige
from phasen import (PHASEN, ANZAHL_PHASEN, einfuehrungstext, phasen_uebersicht)
from pdf_export import erstelle_ergebnis_pdf

# -------------------------------------------------------------
#  Grundeinstellungen
# -------------------------------------------------------------
MODELL = "claude-sonnet-4-6"          # guenstiger als Opus, fuer diesen Zweck ausreichend
MAX_TOKENS = 1500                     # deckelt Ausgabekosten pro Schritt
EXCEL_PFAD = "beispieldaten.xlsx"
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
#  Statische Daten laden (gecached)
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
    """Gibt {dimension: [(kennzahl_id, name, einheit, richtung), ...]} fuer den Typ."""
    aktiv = aktive_kennzahlen(MATRIX, typ)
    gruppen = {}
    for kid in aktiv:
        d = KPI_DEFS[kid].dimension
        gruppen.setdefault(d, []).append(
            (kid, META[kid]["name"], META[kid]["einheit"], KPI_DEFS[kid].richtung))
    return gruppen


def rechne(rohwerte, gewichte, typ):
    """Deterministische Berechnung ueber kennzahlen.py."""
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


def slider_geaendert(geaendert, dims):
    """Auto-Ausgleich der Gewichtsregler: Summe bleibt 100."""
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


def zeige_gewichts_slider(dims, schluessel_praefix=""):
    """Zeichnet die Auto-Ausgleich-Slider. Anzeigename mit Umlaut."""
    for d in dims:
        if f"w_{d}" not in st.session_state:
            st.session_state[f"w_{d}"] = round(st.session_state.gewichte[d] * 100)
    for d in dims:
        st.slider(dim_anzeige(d), min_value=0, max_value=100, key=f"w_{d}",
                  on_change=slider_geaendert, args=(d, dims))
    summe = sum(st.session_state[f"w_{d}"] for d in dims)
    st.write(f"**Summe:** {summe} %")
    return summe


# ---- LLM-Aufruf fuer die textliche Szenario-Zuordnung (Phase 1) ----
def ordne_szenario_typ_zu(nutzertext):
    """Laesst das Modell die Freitext-Antwort einem Matrix-Typ zuordnen.
    Gibt den Typ-Schluessel zurueck oder None."""
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


# ---- Dialog mit dem Bot (Phasen 2, 4, 5, 7 nutzen den Chat) ----
def baue_system_prompt():
    typ = st.session_state.typ
    phase = st.session_state.phase
    aktiv_kids = aktive_kennzahlen(MATRIX, typ)
    kennzahl_liste = ""
    for kid in aktiv_kids:
        m = META[kid]
        kennzahl_liste += (f"- {kid}: {m['name']} "
                           f"(Dimension {m['dimension']}, Einheit {m['einheit']}, "
                           f"Richtung {KPI_DEFS[kid].richtung})\n")
    beschreibung = SZENARIO_BESCHREIBUNGEN.get(typ, "")
    label = SZENARIO_TYP_LABELS.get(typ, typ)

    # In Phase 4 dem Bot die vorhandenen Excel-Werte mitgeben
    excel_hinweis = ""
    if EXCEL_WERTE:
        zeilen = []
        for standort, kvs in EXCEL_WERTE.items():
            relevante = {k: v for k, v in kvs.items() if k in aktiv_kids}
            zeilen.append(f"{standort}: " +
                          ", ".join(f"{k}={v}" for k, v in relevante.items()))
        excel_hinweis = (
            "\nFolgende Werte liegen bereits als Beispieldaten vor (nutze sie, "
            "frage sie NICHT erneut ab):\n" + "\n".join(zeilen) + "\n")

    return f"""Du bist ein Assistent zur Entscheidungsunterstuetzung bei der \
Konfiguration globaler Produktionsnetzwerke. Aktuelle Phase: {phase} \
({PHASEN[phase]['titel']}).

Szenario-Typ: '{label}'. Beschreibung: {beschreibung}

Fuer diesen Typ sind ausschliesslich folgende Kennzahlen relevant:
{kennzahl_liste}{excel_hinweis}
Verhalten je Phase:
- Phase 2: Stelle uebersichtlich dar, welche Kennzahlen relevant sind, \
gruppiert nach Leistungsdimension. Erklaere kurz, dann bitte den Nutzer, mit \
'weiter' zu Phase 3 zu gehen.
- Phase 4: Erfasse fuer MINDESTENS ZWEI Konfigurationen die Kennzahlen. Nutze \
vorhandene Beispieldaten und frage nur fehlende Werte ab. Wenn vollstaendig, \
rufe das Werkzeug 'berechne_nutzwerte' auf. Rechne NIEMALS selbst.
- Phase 7: Gib eine knappe Zusammenfassung: Was wird empfohlen? Was wurde \
beruecksichtigt (Szenario-Typ, Kennzahlen, Gewichtung)? Was sollte bei \
weiteren Entscheidungen zusaetzlich beachtet werden?

Antworte auf Deutsch, sachlich und knapp. Wenige Fragen gleichzeitig."""


def tool_definitionen():
    return [{
        "name": "berechne_nutzwerte",
        "description": ("Berechnet die Nutzwerte aller Szenarien deterministisch. "
                        "Verwenden, sobald alle Kennzahlen vorliegen. Nie selbst rechnen."),
        "input_schema": {
            "type": "object",
            "properties": {
                "rohwerte": {"type": "object",
                             "description": "{Szenarioname: {kennzahl_id: Wert}}"}
            },
            "required": ["rohwerte"],
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
            if aufruf.name == "berechne_nutzwerte":
                rohwerte = aufruf.input["rohwerte"]
                st.session_state.letzte_rohwerte = rohwerte
                erg = rechne(rohwerte, st.session_state.gewichte,
                             st.session_state.typ)
                st.session_state.letztes_ergebnis = erg
                ergebnisse.append({
                    "type": "tool_result", "tool_use_id": aufruf.id,
                    "content": json.dumps(erg, ensure_ascii=False)})
        st.session_state.messages.append({"role": "user", "content": ergebnisse})


def _block_attr(b, name):
    return b.get(name) if isinstance(b, dict) else getattr(b, name, None)


def zeige_verlauf():
    for m in st.session_state.messages:
        if m["role"] == "user":
            inhalt = m["content"]
            if isinstance(inhalt, str):
                with st.chat_message("user"):
                    st.markdown(inhalt)
        elif m["role"] == "assistant" and isinstance(m["content"], list):
            for b in m["content"]:
                if _block_attr(b, "type") == "text":
                    with st.chat_message("assistant"):
                        st.markdown(_block_attr(b, "text"))


def letzter_bot_text():
    """Liefert den letzten reinen Bot-Text (fuer die PDF-Zusammenfassung)."""
    for m in reversed(st.session_state.messages):
        if m["role"] == "assistant" and isinstance(m["content"], list):
            texte = [_block_attr(b, "text") for b in m["content"]
                     if _block_attr(b, "type") == "text"]
            if texte:
                return "\n".join(t for t in texte if t)
    return ""


def naechste_phase():
    if st.session_state.phase < ANZAHL_PHASEN:
        st.session_state.phase += 1


def bot_nachricht_anstossen(text):
    """Sendet eine (versteckte) Nutzernachricht, um den Bot in einer Phase
    antworten zu lassen, ohne dass der Nutzer tippen muss."""
    st.session_state.messages.append({"role": "user", "content": text})
    fuehre_dialog_runde()


# =============================================================
#  Sitzungsspeicher
# =============================================================
for key, default in [("phase", 1), ("typ", None), ("messages", []),
                     ("gewichte", {}), ("dims", []),
                     ("letztes_ergebnis", None), ("letzte_rohwerte", None),
                     ("einfuehrung_gezeigt", False), ("phase2_gezeigt", False),
                     ("phase4_gestartet", False), ("phase7_gezeigt", False)]:
    if key not in st.session_state:
        st.session_state[key] = default

# =============================================================
#  KOPF + PHASENANZEIGE
# =============================================================
st.title("🏭 Entscheidungsmodell: globale Produktionsnetzwerke")

with st.sidebar:
    st.subheader("Fortschritt")
    st.markdown(phasen_uebersicht(st.session_state.phase))

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
    st.caption("Beschreibe in eigenen Worten, worum es geht — ich ordne es dann "
               "dem passenden Szenario-Typ zu.")

    # verfuegbare Typen zur Orientierung
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
                       "formuliere es etwas konkreter oder nenne den Typ direkt.")
        else:
            st.session_state.typ = typ
            aktiv_kids = aktive_kennzahlen(MATRIX, typ)
            dims = dimensionen_im_typ(KPI_DEFS, aktiv_kids)
            st.session_state.dims = dims
            st.session_state.gewichte = {d: 1.0 / len(dims) for d in dims}
            naechste_phase()
            st.rerun()
    st.stop()

# Ab hier ist ein Typ gewaehlt
TYP = st.session_state.typ
DIMS = st.session_state.dims
st.caption(f"Szenario-Typ: **{SZENARIO_TYP_LABELS.get(TYP, TYP)}**")

# =============================================================
#  PHASE 2 — Relevante Kennzahlen anzeigen
# =============================================================
if PHASE == 2:
    st.subheader(PHASEN[2]["titel"])
    st.write("Für den gewählten Szenario-Typ sind die folgenden Kennzahlen "
             "relevant, gruppiert nach Leistungsdimension:")
    gruppen = kennzahlen_nach_dimension(TYP)
    for d in DIMS:
        kzs = gruppen.get(d, [])
        st.markdown(f"**{dim_anzeige(d)}**")
        for kid, name, einheit, richtung in kzs:
            pfeil = "↑ höher ist besser" if richtung == "max" else "↓ niedriger ist besser"
            st.markdown(f"- {name} ({einheit}, {pfeil})")
    st.divider()
    if st.button("Weiter zu Phase 3 (Gewichtung) ▶️"):
        naechste_phase()
        st.rerun()
    st.stop()

# =============================================================
#  PHASE 3 — Gewichtung (Anfangsgewichtung)
# =============================================================
if PHASE == 3:
    st.subheader(PHASEN[3]["titel"])
    st.write("Lege fest, wie wichtig dir die einzelnen Leistungsdimensionen "
             "sind. Ziehst du einen Regler hoch, passen sich die anderen "
             "automatisch an, sodass die Summe stets 100 % ergibt.")
    zeige_gewichts_slider(DIMS)
    st.divider()
    if st.button("Gewichtung übernehmen und zur Datenabfrage ▶️"):
        naechste_phase()
        st.rerun()
    st.stop()

# =============================================================
#  PHASE 4 — Datenabfrage (Chat + Excel)
# =============================================================
if PHASE == 4:
    st.subheader(PHASEN[4]["titel"])
    if EXCEL_WERTE:
        st.caption(f"Beispieldaten geladen für: {', '.join(EXCEL_STANDORTE)}. "
                   "Fehlende Werte frage ich im Chat ab.")
    if not st.session_state.phase4_gestartet:
        st.session_state.phase4_gestartet = True
        with st.spinner("Starte die Datenabfrage …"):
            bot_nachricht_anstossen(
                "Starte Phase 4. Nutze vorhandene Beispieldaten und frage "
                "fehlende Kennzahlen ab. Beginne jetzt.")
        st.rerun()

    zeige_verlauf()

    if st.session_state.letztes_ergebnis is not None:
        st.success("Alle Daten erfasst und berechnet.")
        if st.button("Weiter zu Phase 5 (Berechnung ansehen) ▶️"):
            naechste_phase()
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
#  PHASE 5 — Berechnung transparent darstellen
# =============================================================
if PHASE == 5:
    st.subheader(PHASEN[5]["titel"])
    erg = st.session_state.letztes_ergebnis
    if erg is None:
        st.warning("Es liegt noch kein Ergebnis vor. Bitte zurück zu Phase 4.")
        st.stop()

    st.write("Die Nutzwerte wurden deterministisch berechnet: relative "
             "Min-Max-Normalisierung je Kennzahl, Mittelung je Dimension, "
             "anschließend gewichtete Summe der Dimensionen.")

    st.markdown("**Verwendete Gewichtung:**")
    for d in DIMS:
        st.markdown(f"- {dim_anzeige(d)}: {erg['gewichte'][d]*100:.0f} %")

    st.markdown("**Eingegangene Rohwerte:**")
    if st.session_state.letzte_rohwerte:
        st.dataframe(
            [{"Szenario": s, **{META[k]["name"]: v for k, v in werte.items()}}
             for s, werte in st.session_state.letzte_rohwerte.items()],
            use_container_width=True, hide_index=True)

    st.markdown("**Ergebnis:**")
    st.dataframe(
        [{"Rang": erg["raenge"][s], "Szenario": s, "Nutzwert": nw}
         for s, nw in sorted(erg["nutzwerte"].items(),
                             key=lambda kv: kv[1], reverse=True)],
        use_container_width=True, hide_index=True)
    st.info(f"Empfehlung nach aktueller Gewichtung: **{erg['empfehlung']}**")

    st.divider()
    if st.button("Weiter zu Phase 6 (Sensitivitätsanalyse) ▶️"):
        naechste_phase()
        st.rerun()
    st.stop()

# =============================================================
#  PHASE 6 — Sensitivitaetsanalyse
# =============================================================
if PHASE == 6:
    st.subheader(PHASEN[6]["titel"])
    st.write("Verändere die Gewichtung und beobachte, wie sich Rangfolge und "
             "Nutzwerte verschieben. So prüfst du, wie robust die Empfehlung ist.")
    zeige_gewichts_slider(DIMS)
    if st.button("🔄 Mit aktueller Gewichtung neu berechnen"):
        if st.session_state.letzte_rohwerte is not None:
            st.session_state.letztes_ergebnis = rechne(
                st.session_state.letzte_rohwerte,
                st.session_state.gewichte, TYP)
            st.rerun()

    erg = st.session_state.letztes_ergebnis
    if erg:
        st.markdown("**Aktuelles Ergebnis:**")
        st.dataframe(
            [{"Rang": erg["raenge"][s], "Szenario": s, "Nutzwert": nw}
             for s, nw in sorted(erg["nutzwerte"].items(),
                                 key=lambda kv: kv[1], reverse=True)],
            use_container_width=True, hide_index=True)
        st.info(f"Empfehlung: **{erg['empfehlung']}**")

    st.divider()
    if st.button("Analyse abschließen und Ergebnis erstellen ▶️"):
        naechste_phase()
        st.rerun()
    st.stop()

# =============================================================
#  PHASE 7 — Zusammenfassung + PDF
# =============================================================
if PHASE == 7:
    st.subheader(PHASEN[7]["titel"])
    erg = st.session_state.letztes_ergebnis

    # Bot-Zusammenfassung einmal erzeugen
    if not st.session_state.phase7_gezeigt:
        st.session_state.phase7_gezeigt = True
        with st.spinner("Erstelle die Zusammenfassung …"):
            bot_nachricht_anstossen(
                "Wir sind in Phase 7. Erstelle jetzt die textliche "
                "Abschluss-Zusammenfassung gemaess deinen Vorgaben.")
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

# =============================================================
#  Neustart (immer verfuegbar)
# =============================================================
with st.sidebar:
    st.divider()
    if st.button("🔁 Neue Analyse starten"):
        keys = list(st.session_state.keys())
        for k in keys:
            st.session_state.pop(k, None)
        st.rerun()
