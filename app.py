# =============================================================
#  HAUPTANWENDUNG (Streamlit) - Version 2
# =============================================================
#  Entscheidungsunterstuetzung zur Konfiguration globaler
#  Produktionsnetzwerke.
#
#  Neu in dieser Version:
#   - Nutzer waehlt zu Beginn EINEN Szenario-Typ; die Matrix
#     bestimmt die aktiven Kennzahlen (strikt).
#   - Gewichtungsregler erscheinen ERST nach dem ersten Ergebnis
#     und gleichen sich automatisch auf Summe 100 % aus
#     (Sensitivitaetsanalyse am Ende).
#   - Bot kann aus einem hinterlegten Dokument Kennzahlen suchen.
#   - Berechnung ueber kennzahlen.py (deterministisch).
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

# -------------------------------------------------------------
#  Grundeinstellungen
# -------------------------------------------------------------
MODELL = "claude-opus-4-8"
DOKUMENT_PFAD = "datenquelle.pdf"   # gemeinsames Dokument fuer die Kennzahlensuche
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
#  Matrix + Dokument laden (gecached)
# -------------------------------------------------------------
@st.cache_data
def _lade_matrix():
    return lade_matrix("szenario_kennzahl_matrix.csv")

@st.cache_data
def _lade_dokument_b64():
    if os.path.exists(DOKUMENT_PFAD):
        with open(DOKUMENT_PFAD, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")
    return None

SZENARIO_TYPEN, KPI_DEFS, MATRIX, META = _lade_matrix()
DOKUMENT_B64 = _lade_dokument_b64()

# =============================================================
#  FUNKTIONEN  (alle vor erster Verwendung definiert)
# =============================================================

def tool_definitionen():
    werkzeuge = [{
        "name": "berechne_nutzwerte",
        "description": (
            "Berechnet die Nutzwerte aller Szenarien deterministisch. IMMER "
            "verwenden, sobald fuer alle Szenarien die aktiven Kennzahlen "
            "vorliegen. Niemals selbst rechnen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "rohwerte": {
                    "type": "object",
                    "description": (
                        "{Szenarioname: {kennzahl_id: Rohwert}}. Nur die fuer "
                        "den gewaehlten Szenario-Typ aktiven kennzahl_id "
                        "verwenden."
                    ),
                }
            },
            "required": ["rohwerte"],
        },
    }]
    if DOKUMENT_B64 is not None:
        werkzeuge.append({
            "name": "suche_im_dokument",
            "description": (
                "Durchsucht das hinterlegte Datenquelle-Dokument nach einer "
                "Kennzahl bzw. den zur Berechnung noetigen Rohgroessen. "
                "Verwenden, wenn der Nutzer einen Wert nicht selbst angibt, "
                "sondern auf das Dokument verweist."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "suchbegriff": {
                        "type": "string",
                        "description": "Wonach im Dokument gesucht wird.",
                    }
                },
                "required": ["suchbegriff"],
            },
        })
    return werkzeuge


def baue_system_prompt(typ):
    aktiv_kids = aktive_kennzahlen(MATRIX, typ)
    kennzahl_liste = ""
    for kid in aktiv_kids:
        m = META[kid]
        kennzahl_liste += (f"- {kid}: {m['name']} "
                           f"(Dimension {m['dimension']}, Einheit {m['einheit']}, "
                           f"Richtung {KPI_DEFS[kid].richtung})\n")
    beschreibung = SZENARIO_BESCHREIBUNGEN.get(typ, "")
    label = SZENARIO_TYP_LABELS.get(typ, typ)

    doku_hinweis = ""
    if DOKUMENT_B64 is not None:
        doku_hinweis = (
            "\nEin Datenquelle-Dokument ist hinterlegt. Wenn der Nutzer einen "
            "Wert nicht direkt nennt, nutze das Werkzeug 'suche_im_dokument', "
            "um den Wert dort zu finden, bevor du nachfragst.\n")

    return f"""Du bist ein Assistent zur Entscheidungsunterstuetzung bei der \
Konfiguration globaler Produktionsnetzwerke.

Der Nutzer hat den Szenario-Typ '{label}' gewaehlt.
Beschreibung dieses Typs: {beschreibung}

Innerhalb dieses Typs vergleicht der Nutzer mehrere konkrete Konfigurationen \
(z.B. zwei moegliche Standorte). Fuer DIESEN Typ sind ausschliesslich folgende \
Kennzahlen relevant - erfasse NUR diese, keine anderen:
{kennzahl_liste}
Deine Aufgaben:
1. Erklaere bei Bedarf den Szenario-Typ und die Kennzahlen.
2. Erfasse fuer MINDESTENS ZWEI Konfigurationen die oben gelisteten Kennzahlen \
(als Rohwerte). Frage gezielt und in kleinen Schritten nach.
3. Fuer manche Kennzahlen werden mehrere Rohgroessen benoetigt (z.B. Gutteile \
und Gesamtproduktion fuer die Qualitaetsrate). Frage diese ab; die Formel wird \
im Hintergrund deterministisch berechnet.{doku_hinweis}
4. Wenn fuer alle Konfigurationen die Kennzahlen vorliegen, rufe das Werkzeug \
'berechne_nutzwerte' auf. Rechne NIEMALS selbst.
5. Erklaere das Ergebnis verstaendlich.

Antworte auf Deutsch, sachlich und knapp. Stelle immer nur wenige Fragen \
gleichzeitig."""


def rechne(rohwerte, gewichte, typ):
    """Bereitet die Daten auf und ruft die deterministische Berechnung auf."""
    aktiv_kids = aktive_kennzahlen(MATRIX, typ)
    szenarien = list(rohwerte.keys())

    aktiv = {}
    for s in szenarien:
        aktiv[s] = {kid: (1 if kid in aktiv_kids else 0) for kid in KPI_DEFS}

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


def fuehre_werkzeug_aus(aufruf, typ):
    if aufruf.name == "berechne_nutzwerte":
        rohwerte = aufruf.input["rohwerte"]
        st.session_state.letzte_rohwerte = rohwerte
        ergebnis = rechne(rohwerte, st.session_state.gewichte, typ)
        st.session_state.letztes_ergebnis = ergebnis
        return json.dumps(ergebnis, ensure_ascii=False), False
    if aufruf.name == "suche_im_dokument":
        text = ("Dokument liegt vor. Lies den Wert zum Suchbegriff "
                f"'{aufruf.input['suchbegriff']}' direkt aus dem angehaengten "
                "Dokument ab.")
        return text, True   # zweiter Wert: Dokument anhaengen
    return "Unbekanntes Werkzeug.", False


def fuehre_dialog_runde(typ):
    while True:
        antwort = client.messages.create(
            model=MODELL,
            max_tokens=2000,
            system=baue_system_prompt(typ),
            tools=tool_definitionen(),
            messages=st.session_state.messages,
        )
        st.session_state.messages.append(
            {"role": "assistant", "content": antwort.content})

        tool_aufrufe = [b for b in antwort.content
                        if getattr(b, "type", None) == "tool_use"]
        if not tool_aufrufe:
            return

        tool_ergebnisse = []
        for aufruf in tool_aufrufe:
            ergebnis_text, doku_anhaengen = fuehre_werkzeug_aus(aufruf, typ)
            if doku_anhaengen and DOKUMENT_B64 is not None:
                inhalt = [
                    {"type": "text", "text": ergebnis_text},
                    {"type": "document",
                     "source": {"type": "base64",
                                "media_type": "application/pdf",
                                "data": DOKUMENT_B64}},
                ]
            else:
                inhalt = ergebnis_text
            tool_ergebnisse.append({
                "type": "tool_result",
                "tool_use_id": aufruf.id,
                "content": inhalt,
            })
        st.session_state.messages.append(
            {"role": "user", "content": tool_ergebnisse})


def _block_attr(b, name):
    if isinstance(b, dict):
        return b.get(name)
    return getattr(b, name, None)


def zeige_verlauf():
    for m in st.session_state.messages:
        if m["role"] == "user":
            inhalt = m["content"]
            if isinstance(inhalt, list):
                texte = [_block_attr(b, "text") for b in inhalt
                         if _block_attr(b, "type") == "text"]
                if texte and texte[0]:
                    with st.chat_message("user"):
                        st.markdown(texte[0])
            elif isinstance(inhalt, str):
                with st.chat_message("user"):
                    st.markdown(inhalt)
        elif m["role"] == "assistant":
            if isinstance(m["content"], list):
                for b in m["content"]:
                    if _block_attr(b, "type") == "text":
                        with st.chat_message("assistant"):
                            st.markdown(_block_attr(b, "text"))


def slider_geaendert(geaendert, dims):
    """Auto-Ausgleich: aendert sich ein Regler, werden die uebrigen so
    skaliert, dass die Summe wieder 100 ergibt."""
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
        # Rest auf den letzten Regler, damit die Summe exakt 100 ist
        st.session_state[f"w_{andere[-1]}"] = rest_neu - verteilt
    for d in dims:
        st.session_state.gewichte[d] = st.session_state[f"w_{d}"] / 100.0


# =============================================================
#  Sitzungsspeicher initialisieren
# =============================================================
for key, default in [("typ", None), ("messages", []), ("gewichte", {}),
                     ("letztes_ergebnis", None), ("letzte_rohwerte", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# =============================================================
#  OBERFLAECHE
# =============================================================
st.title("🏭 Entscheidungsmodell: globale Produktionsnetzwerke")

# ---- Schritt 1: Szenario-Typ waehlen ----
if st.session_state.typ is None:
    st.subheader("Schritt 1: Szenario-Typ waehlen")
    st.caption("Der gewaehlte Typ bestimmt, welche Kennzahlen verglichen werden.")
    auswahl = st.selectbox(
        "Welche Art von Entscheidung moechtest du untersuchen?",
        options=SZENARIO_TYPEN,
        format_func=lambda t: SZENARIO_TYP_LABELS.get(t, t),
    )
    if auswahl:
        st.info(SZENARIO_BESCHREIBUNGEN.get(auswahl, ""))
    if st.button("Diesen Szenario-Typ waehlen und starten"):
        st.session_state.typ = auswahl
        aktiv_kids = aktive_kennzahlen(MATRIX, auswahl)
        dims = dimensionen_im_typ(KPI_DEFS, aktiv_kids)
        st.session_state.gewichte = {d: 1.0 / len(dims) for d in dims}
        st.rerun()
    st.stop()

TYP = st.session_state.typ
DIMENSIONEN_AKTIV = list(st.session_state.gewichte.keys())
st.caption(f"Gewaehlter Szenario-Typ: **{SZENARIO_TYP_LABELS.get(TYP, TYP)}**")

# ---- Chatverlauf ----
zeige_verlauf()

eingabe = st.chat_input("Beschreibe deine Konfigurationen oder gib Kennzahlen ein …")
if eingabe:
    st.session_state.messages.append({"role": "user", "content": eingabe})
    with st.chat_message("user"):
        st.markdown(eingabe)
    with st.spinner("Der Assistent denkt nach …"):
        fuehre_dialog_runde(TYP)
    st.rerun()

# ---- Ergebnis + Sensitivitaetsanalyse (erst NACH erstem Ergebnis) ----
if st.session_state.letztes_ergebnis:
    erg = st.session_state.letztes_ergebnis
    st.divider()
    st.subheader("📊 Ergebnis")
    st.markdown(f"**Empfehlung:** {erg['empfehlung']}")
    tabelle = [{"Szenario": s, "Rang": erg["raenge"][s], "Nutzwert": nw}
               for s, nw in sorted(erg["nutzwerte"].items(),
                                   key=lambda kv: kv[1], reverse=True)]
    st.dataframe(tabelle, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🔬 Sensitivitaetsanalyse")
    st.caption("Veraendere die Gewichtung. Die uebrigen Regler passen sich "
               "automatisch an, sodass die Summe stets 100 % bleibt.")

    # Slider-Keys initialisieren (vor Erzeugung der Widgets, ohne value=)
    for d in DIMENSIONEN_AKTIV:
        if f"w_{d}" not in st.session_state:
            st.session_state[f"w_{d}"] = round(st.session_state.gewichte[d] * 100)

    for d in DIMENSIONEN_AKTIV:
        st.slider(d, min_value=0, max_value=100, key=f"w_{d}",
                  on_change=slider_geaendert, args=(d, DIMENSIONEN_AKTIV))

    summe = sum(st.session_state[f"w_{d}"] for d in DIMENSIONEN_AKTIV)
    st.write(f"**Summe:** {summe} %")

    if st.button("🔄 Mit diesen Gewichten neu berechnen"):
        if st.session_state.letzte_rohwerte is not None:
            st.session_state.letztes_ergebnis = rechne(
                st.session_state.letzte_rohwerte,
                st.session_state.gewichte, TYP)
            st.rerun()

# ---- Neustart ----
st.divider()
if st.button("🔁 Neue Analyse starten (Szenario-Typ wechseln)"):
    keys = (["typ", "messages", "gewichte", "letztes_ergebnis", "letzte_rohwerte"]
            + [f"w_{d}" for d in DIMENSIONEN_AKTIV])
    for k in keys:
        st.session_state.pop(k, None)
    st.rerun()
