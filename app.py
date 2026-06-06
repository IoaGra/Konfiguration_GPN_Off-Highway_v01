# =============================================================
#  HAUPTANWENDUNG (Streamlit)
# =============================================================
#  Entscheidungsunterstuetzung zur Konfiguration globaler
#  Produktionsnetzwerke.
#
#  Architektur ("LLM as orchestrator, not as calculator"):
#    - Das Sprachmodell (Claude) fuehrt den Dialog, erfasst
#      Werte und extrahiert sie aus Dokumenten.
#    - Die NUTZWERTE werden ausschliesslich in berechnung.py
#      deterministisch berechnet (per Function Calling).
#    - Variante A: Datenqualitaet wird getrennt ausgewiesen.
# =============================================================

import json
import base64
import streamlit as st
import anthropic

from config import DIMENSIONEN, STARTGEWICHTE, DATENQUALITAET
from berechnung import berechne

# -------------------------------------------------------------
#  Grundeinstellungen
# -------------------------------------------------------------
MODELL = "claude-opus-4-8"   # aktuelles Modell; bei Bedarf anpassbar
st.set_page_config(page_title="Entscheidungsmodell Produktionsnetzwerke",
                   page_icon="🏭", layout="wide")

# -------------------------------------------------------------
#  API-Schluessel aus den Streamlit-Secrets laden
# -------------------------------------------------------------
try:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    st.error("Kein API-Schluessel gefunden. Bitte in den App-Einstellungen "
             "unter 'Secrets' den Eintrag ANTHROPIC_API_KEY hinterlegen.")
    st.stop()

# -------------------------------------------------------------
#  Werkzeug-Definition fuer das Sprachmodell (Function Calling)
#  Das Modell befuellt die Parameter; gerechnet wird in Python.
# -------------------------------------------------------------
TOOL_BESCHREIBUNG = [{
    "name": "berechne_nutzwerte",
    "description": (
        "Berechnet die Nutzwerte und die Datenqualitaet aller Szenarien "
        "deterministisch nach dem hinterlegten Entscheidungsmodell. "
        "IMMER dieses Werkzeug verwenden, sobald die Kennzahlen aller "
        "Szenarien vollstaendig vorliegen. Niemals selbst rechnen."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "szenarien": {
                "type": "object",
                "description": (
                    "Objekt mit Szenarionamen als Schluessel. Je Szenario ein "
                    "Objekt mit den Dimensionen, je Dimension die Kennzahlen mit "
                    "'wert' (Zahl) und 'quelle_q' (Datenqualitaet: 1.0 Nutzer-"
                    "eingabe, 0.7 Dokumentenextraktion, 0.3 Schaetzung)."
                ),
            }
        },
        "required": ["szenarien"],
    },
}]

# -------------------------------------------------------------
#  System-Prompt: definiert das Verhalten des Bots
# -------------------------------------------------------------
def baue_system_prompt():
    dim_text = ""
    for dim, inhalt in DIMENSIONEN.items():
        kzs = ", ".join(f"{k['name']} ({k['einheit']}, {k['richtung']})"
                        for k in inhalt["kennzahlen"])
        dim_text += f"- {dim}: {kzs}\n"
    return f"""Du bist ein Assistent zur Entscheidungsunterstuetzung bei der \
Konfiguration globaler Produktionsnetzwerke. Du fuehrst den Nutzer durch den \
Vergleich mehrerer Szenarien (Standortkonfigurationen).

Das Modell umfasst folgende Leistungsdimensionen und Kennzahlen:
{dim_text}
Deine Aufgaben:
1. Erfasse fuer MINDESTENS ZWEI Szenarien alle Kennzahlen. Frage gezielt und \
freundlich nach fehlenden Werten.
2. Werte koennen drei Quellen haben - vermerke je Wert die Datenqualitaet:
   - Nutzereingabe = 1.0
   - aus einem hochgeladenen Dokument extrahiert = 0.7
   - von dir geschaetzt (worst case), wenn keine Angabe vorliegt = 0.3
   Wenn du schaetzt, weise den Nutzer transparent darauf hin.
3. Wenn alle Kennzahlen aller Szenarien vorliegen, rufe das Werkzeug \
'berechne_nutzwerte' auf. Rechne NIEMALS selbst - die Berechnung erfolgt \
ausschliesslich ueber das Werkzeug.
4. Erklaere dem Nutzer das Ergebnis verstaendlich: Rangfolge, Nutzwerte, \
Datenqualitaet und welche Dimensionen ausschlaggebend waren.

Antworte auf Deutsch, sachlich und knapp. Stelle immer nur wenige Fragen \
gleichzeitig, um den Nutzer nicht zu ueberfordern."""

# -------------------------------------------------------------
#  Sitzungsspeicher (pro Nutzer isoliert)
# -------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []   # Verlauf fuer die API
if "letzte_gewichte" not in st.session_state:
    st.session_state.letzte_gewichte = dict(STARTGEWICHTE)
if "letztes_ergebnis" not in st.session_state:
    st.session_state.letztes_ergebnis = None
if "letzte_szenarien" not in st.session_state:
    st.session_state.letzte_szenarien = None

# =============================================================
#  SEITENLEISTE: Gewichtung der Dimensionen (iterativ)
# =============================================================
st.sidebar.title("⚖️ Gewichtung der Dimensionen")
st.sidebar.caption("Passe die Gewichte an. Die Summe wird automatisch auf "
                   "100 % normiert. Nach jeder Aenderung neu berechnen.")

roh_gewichte = {}
for dim in DIMENSIONEN:
    roh_gewichte[dim] = st.sidebar.slider(
        dim, min_value=0.0, max_value=1.0,
        value=float(st.session_state.letzte_gewichte.get(dim, 0.2)),
        step=0.05,
    )
st.session_state.letzte_gewichte = roh_gewichte

summe = sum(roh_gewichte.values())
if summe > 0:
    st.sidebar.markdown("**Normierte Gewichte:**")
    for dim, w in roh_gewichte.items():
        st.sidebar.write(f"- {dim}: {w/summe:.0%}")

neu_berechnen = st.sidebar.button("🔄 Mit neuen Gewichten neu berechnen")

# =============================================================
#  HAUPTBEREICH
# =============================================================
st.title("🏭 Entscheidungsmodell: globale Produktionsnetzwerke")
st.caption("Vergleiche Szenarien anhand gewichteter Leistungsdimensionen. "
           "Die Berechnung erfolgt deterministisch; die Datenqualitaet wird "
           "getrennt ausgewiesen.")

# ---- Dokument-Upload --------------------------------------------------
with st.expander("📎 Optional: Dokument hochladen (PDF), aus dem Werte extrahiert werden"):
    upload = st.file_uploader("PDF auswaehlen", type=["pdf"])
    if upload is not None and st.button("Werte aus Dokument lesen"):
        pdf_b64 = base64.standard_b64encode(upload.read()).decode("utf-8")
        st.session_state.messages.append({
            "role": "user",
            "content": [
                {"type": "document",
                 "source": {"type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64}},
                {"type": "text",
                 "text": ("Bitte lies relevante Kennzahlen aus diesem Dokument "
                          "aus und ordne sie den Szenarien zu. Markiere diese "
                          "Werte als Datenqualitaet 0.7 (Dokumentenextraktion).")},
            ],
        })
        st.rerun()

# ---- Bisherigen Verlauf anzeigen -------------------------------------
def zeige_verlauf():
    for m in st.session_state.messages:
        if m["role"] == "user":
            inhalt = m["content"]
            if isinstance(inhalt, list):
                texte = [b["text"] for b in inhalt if b.get("type") == "text"]
                if texte:
                    with st.chat_message("user"):
                        st.markdown(texte[0])
            else:
                with st.chat_message("user"):
                    st.markdown(inhalt)
        elif m["role"] == "assistant":
            if isinstance(m["content"], list):
                for b in m["content"]:
                    if b.get("type") == "text":
                        with st.chat_message("assistant"):
                            st.markdown(b["text"])

zeige_verlauf()

# =============================================================
#  KERN: eine Dialogrunde mit dem Modell abwickeln
#  (inkl. Function Calling -> deterministische Berechnung)
# =============================================================
def fuehre_dialog_runde(roh_gewichte):
    """Schickt den Verlauf an Claude. Falls Claude das Werkzeug aufruft,
    wird in Python gerechnet und das Ergebnis zurueckgegeben."""
    while True:
        antwort = client.messages.create(
            model=MODELL,
            max_tokens=2000,
            system=baue_system_prompt(),
            tools=TOOL_BESCHREIBUNG,
            messages=st.session_state.messages,
        )

        # Antwort des Modells in den Verlauf aufnehmen
        st.session_state.messages.append(
            {"role": "assistant", "content": antwort.content})

        # Pruefen, ob das Modell das Rechen-Werkzeug aufrufen will
        tool_aufrufe = [b for b in antwort.content
                        if getattr(b, "type", None) == "tool_use"]

        if not tool_aufrufe:
            # Keine Berechnung noetig -> Dialog fertig
            return

        # --- Werkzeug ausfuehren: HIER wird deterministisch gerechnet ---
        tool_ergebnisse = []
        for aufruf in tool_aufrufe:
            if aufruf.name == "berechne_nutzwerte":
                szenarien = aufruf.input["szenarien"]
                st.session_state.letzte_szenarien = szenarien
                ergebnis = berechne(szenarien, roh_gewichte)
                st.session_state.letztes_ergebnis = ergebnis
                tool_ergebnisse.append({
                    "type": "tool_result",
                    "tool_use_id": aufruf.id,
                    "content": json.dumps(ergebnis, ensure_ascii=False),
                })

        # Ergebnis zurueck an das Modell, damit es erklaeren kann
        st.session_state.messages.append(
            {"role": "user", "content": tool_ergebnisse})
        # Schleife laeuft erneut -> Modell formuliert die Erklaerung

# ---- Neuberechnung mit geaenderten Gewichten -------------------------
if neu_berechnen and st.session_state.letzte_szenarien is not None:
    ergebnis = berechne(st.session_state.letzte_szenarien, roh_gewichte)
    st.session_state.letztes_ergebnis = ergebnis
    st.success("Neu berechnet mit den aktuellen Gewichten.")

# ---- Eingabezeile ----------------------------------------------------
eingabe = st.chat_input("Beschreibe deine Szenarien oder gib Kennzahlen ein …")
if eingabe:
    st.session_state.messages.append({"role": "user", "content": eingabe})
    with st.chat_message("user"):
        st.markdown(eingabe)
    with st.spinner("Der Assistent denkt nach …"):
        fuehre_dialog_runde(roh_gewichte)
    st.rerun()

# =============================================================
#  ERGEBNISDARSTELLUNG
# =============================================================
if st.session_state.letztes_ergebnis:
    erg = st.session_state.letztes_ergebnis
    st.divider()
    st.subheader("📊 Ergebnis")
    st.markdown(f"**Empfehlung:** {erg['empfehlung']}")

    # Tabelle: Nutzwert, Datenqualitaet, Rang
    tabelle = []
    for name, daten in erg["szenarien"].items():
        zeile = {
            "Szenario": name,
            "Rang": daten["rang"],
            "Nutzwert": daten["nutzwert"],
            "Datenqualitaet": daten["datenqualitaet"],
        }
        zeile.update({d: daten["dimensionen"][d] for d in DIMENSIONEN})
        tabelle.append(zeile)
    tabelle.sort(key=lambda z: z["Rang"])
    st.dataframe(tabelle, use_container_width=True, hide_index=True)

    st.caption("Hinweis (Variante A): Die Datenqualitaet fliesst NICHT in den "
               "Nutzwert ein, sondern dient als getrenntes Konfidenzmass.")
