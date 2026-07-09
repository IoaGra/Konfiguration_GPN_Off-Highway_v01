# =============================================================
#  HAUPTANWENDUNG (Streamlit) - validierungsorientierte Version
# =============================================================
#  Entscheidungsassistent fuer die Konfiguration globaler
#  Produktionsnetzwerke (Off-Highway-Motorenbranche).
#
#  Grundprinzip:
#   - Claude fuehrt den Dialog und steuert die Phasen.
#   - Alle Berechnungen erfolgen deterministisch im Python-Code.
#   - Die Kennzahlenauswahl erfolgt im Hintergrund ueber die Matrix.
#   - Die Ergebnis-PDF dokumentiert die initiale Gewichtung aus Phase 2.
# =============================================================

import json
import streamlit as st
import anthropic

from berechnung import berechne_nutzwerte
from formeln import (berechne_formel_kennzahl, formel_hinweis_fuer_prompt,
                     ist_formel_kennzahl)
from daten import lade_daten, dimensionen_aus_kpis
from matrix import lade_matrix, aktive_kennzahlen
from szenarien import SZENARIO_BESCHREIBUNGEN
from dimensionen import DIMENSION_BESCHREIBUNGEN
from phasen import PHASEN, ANZAHL_PHASEN
from pdf_export import erstelle_ergebnis_pdf

# -------------------------------------------------------------
# Modell und Tokenlimit
# -------------------------------------------------------------
# Anthropic API-ID fuer Claude Opus. Bei Bedarf in Streamlit Secrets
# mit CLAUDE_MODEL ueberschreiben.
MODELL = st.secrets.get("CLAUDE_MODEL", "claude-opus-4-8")
MAX_TOKENS = 1100
HERKUNFT_LABEL = {"system": "aus System", "nutzer": "Nutzereingabe"}
AUTO_MARKER = "[AUTO]"

st.set_page_config(page_title="Entscheidungsmodell Produktionsnetzwerke",
                   page_icon="🏭", layout="wide")

try:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    st.error("Kein API-Schlüssel gefunden. Bitte in den App-Einstellungen "
             "unter 'Secrets' den Eintrag ANTHROPIC_API_KEY hinterlegen.")
    st.stop()


# -------------------------------------------------------------
#  Statische Daten (gecached)
# -------------------------------------------------------------
@st.cache_data
def _lade_alles():
    kpis, optionen, werte, fehlend = lade_daten("daten.xlsx")
    typen, mat = lade_matrix("szenario_kennzahl_matrix.xlsx")
    return kpis, optionen, werte, fehlend, typen, mat


KPIS, ALLE_OPTIONEN, SYSTEM_WERTE, FEHLEND, SZENARIO_TYPEN, MATRIX = _lade_alles()
ALLE_DIMENSIONEN = dimensionen_aus_kpis(KPIS)


# =============================================================
#  HILFSFUNKTIONEN (deterministisch)
# =============================================================

def baue_rohwerte():
    """Fuegt System-Werte und Nutzer-Werte fuer die gewaehlten Optionen
    zusammen. Rueckgabe: (rohwerte, herkunft) je {option: {kennzahl: ...}}.
    """
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ) if st.session_state.typ else []
    rohwerte, herkunft = {}, {}
    for opt in st.session_state.optionen:
        rohwerte[opt], herkunft[opt] = {}, {}
        for k in aktiv:
            if k in SYSTEM_WERTE.get(opt, {}):
                rohwerte[opt][k] = SYSTEM_WERTE[opt][k]
                herkunft[opt][k] = "system"
        for k, v in st.session_state.nutzer_werte.get(opt, {}).items():
            rohwerte[opt][k] = v
            herkunft[opt][k] = "nutzer"
    return rohwerte, herkunft


def offene_werte():
    """Welche aktiven Kennzahlen fehlen je gewaehlter Option noch?"""
    if not st.session_state.typ:
        return {}
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    rohwerte, _ = baue_rohwerte()
    offen = {}
    for opt in st.session_state.optionen:
        fehlt = [k for k in aktiv if k not in rohwerte.get(opt, {})]
        if fehlt:
            offen[opt] = fehlt
    return offen


def rechne_mit_gewichten(gewichte):
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    rohwerte, herkunft = baue_rohwerte()
    erg = berechne_nutzwerte(rohwerte, aktiv, KPIS, gewichte)
    erg["rohwerte"] = rohwerte
    erg["herkunft"] = herkunft
    return erg


def rechne():
    return rechne_mit_gewichten(st.session_state.gewichte)


def slider_geaendert(geaendert, dims, ziel_key="gewichte"):
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
        st.session_state[ziel_key][d] = st.session_state[f"w_{d}"] / 100.0


def zeige_gewichts_slider(dims, ziel_key="gewichte"):
    for d in dims:
        if f"w_{d}" not in st.session_state:
            st.session_state[f"w_{d}"] = round(st.session_state[ziel_key][d] * 100)
    for d in dims:
        st.slider(d, min_value=0, max_value=100, key=f"w_{d}",
                  on_change=slider_geaendert, args=(d, dims, ziel_key))
    summe = sum(st.session_state[f"w_{d}"] for d in dims)
    st.write(f"**Summe:** {summe} %")


def setze_slider_aus_gewichten(gewichte):
    for d in ALLE_DIMENSIONEN:
        st.session_state[f"w_{d}"] = round(gewichte.get(d, 0) * 100)


def _block_attr(b, name):
    return b.get(name) if isinstance(b, dict) else getattr(b, name, None)


def zeige_verlauf():
    for m in st.session_state.messages:
        if m["role"] == "user":
            if isinstance(m["content"], str) and not m["content"].startswith(AUTO_MARKER):
                with st.chat_message("user"):
                    st.markdown(m["content"])
        elif m["role"] == "assistant" and isinstance(m["content"], list):
            for b in m["content"]:
                if _block_attr(b, "type") == "text":
                    txt = _block_attr(b, "text")
                    if txt:
                        with st.chat_message("assistant"):
                            st.markdown(txt)


def letzter_bot_text():
    for m in reversed(st.session_state.messages):
        if m["role"] == "assistant" and isinstance(m["content"], list):
            texte = [_block_attr(b, "text") for b in m["content"]
                     if _block_attr(b, "type") == "text"]
            texte = [t for t in texte if t]
            if texte:
                return "\n".join(texte)
    return ""


# =============================================================
#  SPRACHMODELL: System-Prompt + Werkzeuge
# =============================================================

def _kompakte_beschreibungen():
    """Tokenarme Beschreibungen nur fuer Phasen, in denen Nachfragen
    wahrscheinlich sind.
    """
    if st.session_state.phase > 2:
        return ""
    return (
        "\nKurzbeschreibungen Szenarien: "
        + json.dumps(SZENARIO_BESCHREIBUNGEN, ensure_ascii=False)
        + "\nKurzbeschreibungen Leistungsdimensionen: "
        + json.dumps(DIMENSION_BESCHREIBUNGEN, ensure_ascii=False)
    )


def baue_system_prompt():
    phase = st.session_state.phase
    typ = st.session_state.typ

    szenario_namen = ", ".join(SZENARIO_TYPEN)
    options_namen = ", ".join(ALLE_OPTIONEN)
    dims = ", ".join(ALLE_DIMENSIONEN)

    kontext = ""
    if typ:
        aktiv = aktive_kennzahlen(MATRIX, typ)
        kontext += (
            f"\nGewaehlter Szenario-Typ: {typ}. "
            f"Gewaehlte Optionen: {', '.join(st.session_state.optionen)}. "
            f"Aktive Kennzahlen laut Matrix: {', '.join(aktiv)}."
        )

    if phase == 3 and typ:
        offen = offene_werte()
        if offen:
            kontext += (
                "\nIn Phase 3 muessen diese fehlenden Werte abgefragt werden: "
                + "; ".join(f"{o}: {', '.join(ks)}" for o, ks in offen.items())
                + "\nAbfragehinweise:\n"
                + formel_hinweis_fuer_prompt(offen)
            )
        else:
            kontext += "\nAlle Werte liegen vor."

    if phase == 4 and st.session_state.basis_ergebnis:
        erg = st.session_state.basis_ergebnis
        kompakt = {
            "gewichte": erg["gewichte"],
            "dim_scores": erg["dim_scores"],
            "nutzwerte": erg["nutzwerte"],
            "raenge": erg["raenge"],
            "empfehlung": erg["empfehlung"],
        }
        kontext += "\nBerechnungsergebnis: " + json.dumps(kompakt, ensure_ascii=False)

    if phase == 5:
        if st.session_state.basis_ergebnis:
            kontext += (
                "\nInitiale Empfehlung aus Phase 4: "
                f"{st.session_state.basis_ergebnis.get('empfehlung')}."
            )
        if st.session_state.sensitivitaet_ergebnis:
            se = st.session_state.sensitivitaet_ergebnis
            kompakt = {
                "gewichte": se["gewichte"],
                "nutzwerte": se["nutzwerte"],
                "raenge": se["raenge"],
                "empfehlung": se["empfehlung"],
            }
            kontext += "\nLetztes Ergebnis der Sensitivitaetsanalyse: " + json.dumps(kompakt, ensure_ascii=False)

    if phase == 6 and st.session_state.basis_ergebnis:
        erg = st.session_state.basis_ergebnis
        kompakt = {
            "gewichte": erg["gewichte"],
            "dim_scores": erg["dim_scores"],
            "nutzwerte": erg["nutzwerte"],
            "raenge": erg["raenge"],
            "empfehlung": erg["empfehlung"],
            "normwerte": erg["normwerte"],
            "herkunft": erg["herkunft"],
            "robustheit": st.session_state.robustheit,
        }
        kontext += "\nERGEBNIS FUER ZUSAMMENFASSUNG: " + json.dumps(kompakt, ensure_ascii=False)

    phasen_anweisung = {
        0: (
            "Begruesse den Nutzer. Erklaere knapp, dass der Chatbot durch "
            "Szenarioauswahl, Gewichtung, Datenabfrage, Berechnung, "
            "Sensitivitaetsanalyse und Zusammenfassung fuehrt. Frage am Ende, "
            "ob es losgehen kann. Wenn der Nutzer zustimmt, rufe naechste_phase auf."
        ),
        1: (
            "Nenne die verfuegbaren Szenario-Typen nur mit Namen. Der Nutzer "
            "muss einen Typ und mindestens zwei Optionen waehlen. Fuer die "
            "Validierung ist vorgesehen: 'Verlagerung der Produktion an anderen "
            "Standort' mit Standort A und Standort B. Wenn Typ und Optionen klar "
            "sind, rufe setze_szenarien auf."
        ),
        2: (
            "Die Gewichtung erfolgt ueber Schieberegler in der App. Erklaere "
            "kurz die fuenf Leistungsdimensionen nur bei Bedarf. Wenn der Nutzer "
            "im Chat schreibt, dass es weitergehen soll, rufe naechste_phase auf."
        ),
        3: (
            "Erklaere: In dieser Phase werden Daten abgefragt. Einige Daten "
            "liegen bereits im System vor, die restlichen Werte benoetigst du "
            "vom Nutzer. Nenne einmal kompakt, welche Kennzahlen fuer das "
            "Szenario relevant sind. Frage die fehlenden Werte anschliessend "
            "schrittweise ab. Bei Formel-Kennzahlen frage nur die angegebenen "
            "Faktoren ab und rufe speichere_fehlende_werte auf. Rechne niemals "
            "selbst. Wenn alle Werte vorliegen und der Nutzer bereit ist, rufe "
            "naechste_phase auf."
        ),
        4: (
            "Die Berechnung wird in der App angezeigt. Erklaere nur auf Wunsch "
            "Details zur Normierungsformel. Wenn der Nutzer weiter moechte, rufe "
            "naechste_phase auf."
        ),
        5: (
            "Der Nutzer testet die Robustheit, indem er die Gewichtungen in der "
            "App variiert und neu berechnet. Bitte ihn danach um eine klare "
            "Einschaetzung, ob das Ergebnis robust ist oder nicht. Sobald diese "
            "Einschaetzung vorliegt, rufe speichere_robustheit auf."
        ),
        6: (
            "Erstelle die Abschluss-Zusammenfassung entlang der Phasen: Szenario "
            "und Optionen, relevante Kennzahlen, initiale Gewichtung, Datenherkunft, "
            "Normierungsformel, Dimensions-Scores, Nutzwerte, Empfehlung und "
            "Robustheitsbewertung. Nutze nur Zahlen aus dem Kontext. Beende deine "
            "Antwort zwingend mit den Abschnitten:\n"
            "ZUSAMMENFASSUNG:\n- ...\n"
            "WEITERE BETRACHTUNG:\n- ..."
        ),
    }[phase]

    return f"""Du bist ein Entscheidungsassistent fuer die Konfiguration globaler Produktionsnetzwerke in der Off-Highway-Motorenbranche.

Verfuegbare Szenario-Typen: {szenario_namen}
Verfuegbare Optionen: {options_namen}
Leistungsdimensionen: {dims}

Regeln:
- Alle numerischen Berechnungen erfolgen ausschliesslich im Anwendungscode.
- Du berechnest keine Scores, Nutzwerte, Normierungen, Mittelwerte oder Rankings selbst.
- Bleibe in der aktuellen Phase und fuehre den Nutzer knapp und dialogorientiert.
- Erklaere Szenarien und Leistungsdimensionen nur auf Nachfrage.
- Frage fehlende Informationen gezielt und schrittweise ab.
- Antworte auf Deutsch.

Aktuelle Phase {phase}: {PHASEN[phase]['titel']}
{phasen_anweisung}
{kontext}
{_kompakte_beschreibungen()}
"""


def tool_definitionen():
    werkzeuge = [{
        "name": "naechste_phase",
        "description": "Schaltet zur naechsten Phase weiter.",
        "input_schema": {"type": "object", "properties": {}},
    }]

    if st.session_state.phase == 1:
        werkzeuge.append({
            "name": "setze_szenarien",
            "description": "Legt Szenario-Typ und Optionen fest und schaltet zur Gewichtung.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "typ": {"type": "string"},
                    "optionen": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["typ", "optionen"],
            },
        })

    if st.session_state.phase == 3:
        werkzeuge.append({
            "name": "speichere_fehlende_werte",
            "description": "Speichert fehlende Werte. Formel-Kennzahlen als Faktor-Objekt angeben.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "werte": {
                        "type": "object",
                        "description": "{Option: {Kennzahl: Zahl ODER Faktor-Objekt}}",
                    }
                },
                "required": ["werte"],
            },
        })

    if st.session_state.phase == 5:
        werkzeuge.append({
            "name": "speichere_robustheit",
            "description": "Speichert die Robustheitsbewertung des Nutzers nach der Sensitivitaetsanalyse.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "bewertung": {
                        "type": "string",
                        "description": "robust, nicht robust oder unklar",
                    },
                    "begruendung": {"type": "string"},
                },
                "required": ["bewertung"],
            },
        })

    return werkzeuge


def fuehre_werkzeug_aus(aufruf):
    if aufruf.name == "naechste_phase":
        if st.session_state.phase < ANZAHL_PHASEN - 1:
            st.session_state.phase += 1
        return f"Phase gewechselt. Aktuelle Phase: {st.session_state.phase}."

    if aufruf.name == "setze_szenarien":
        typ = (aufruf.input.get("typ") or "").strip()
        optionen = aufruf.input.get("optionen") or []
        if typ not in SZENARIO_TYPEN:
            return f"Unbekannter Szenario-Typ '{typ}'. Verfuegbar: {', '.join(SZENARIO_TYPEN)}."
        gueltige = [o for o in optionen if o in ALLE_OPTIONEN]
        if len(gueltige) < 2:
            return f"Mindestens zwei gueltige Optionen noetig. Verfuegbar: {', '.join(ALLE_OPTIONEN)}."
        st.session_state.typ = typ
        st.session_state.optionen = gueltige
        st.session_state.gewichte = {d: 1.0 / len(ALLE_DIMENSIONEN) for d in ALLE_DIMENSIONEN}
        st.session_state.basis_ergebnis = None
        st.session_state.sensitivitaet_ergebnis = None
        st.session_state.robustheit = None
        st.session_state.phase = 2
        return f"Szenario gesetzt: {typ} mit Optionen {', '.join(gueltige)}. Phase 2 ist aktiv."

    if aufruf.name == "speichere_fehlende_werte":
        werte = aufruf.input.get("werte") or {}
        gespeichert = []
        for opt, kvs in werte.items():
            if opt not in st.session_state.optionen or not isinstance(kvs, dict):
                continue
            ziel = st.session_state.nutzer_werte.setdefault(opt, {})
            for k, v in kvs.items():
                if k not in KPIS:
                    continue
                if isinstance(v, dict) and ist_formel_kennzahl(k, opt):
                    ergebnis = berechne_formel_kennzahl(k, v)
                    if ergebnis is not None:
                        ziel[k] = ergebnis
                        gespeichert.append(f"{opt}: {k} (aus Faktoren berechnet)")
                else:
                    try:
                        ziel[k] = float(v)
                        gespeichert.append(f"{opt}: {k}")
                    except (TypeError, ValueError):
                        continue
        offen = offene_werte()
        if offen:
            return (
                "Gespeichert: " + ("; ".join(gespeichert) if gespeichert else "nichts")
                + ". Es fehlen noch: "
                + "; ".join(f"{o}: {', '.join(ks)}" for o, ks in offen.items())
                + ". Bitte weiter schrittweise abfragen."
            )
        return (
            "Gespeichert: " + ("; ".join(gespeichert) if gespeichert else "nichts")
            + ". Alle Werte liegen vor. Frage, ob zur Berechnung gewechselt werden soll."
        )

    if aufruf.name == "speichere_robustheit":
        bewertung = (aufruf.input.get("bewertung") or "").strip()
        begruendung = (aufruf.input.get("begruendung") or "").strip()
        st.session_state.robustheit = {"bewertung": bewertung, "begruendung": begruendung}
        st.session_state.phase = 6
        return "Robustheitsbewertung gespeichert. Phase 6 ist aktiv."

    return "Unbekanntes Werkzeug."


def fuehre_dialog_runde():
    while True:
        try:
            antwort = client.messages.create(
                model=MODELL,
                max_tokens=MAX_TOKENS,
                system=baue_system_prompt(),
                tools=tool_definitionen(),
                messages=st.session_state.messages,
            )
        except Exception as e:
            st.error("Verbindung zum Sprachmodell fehlgeschlagen. Bitte Seite neu laden "
                     f"und erneut versuchen. (Details: {type(e).__name__})")
            return

        st.session_state.messages.append({"role": "assistant", "content": antwort.content})
        tool_aufrufe = [b for b in antwort.content if getattr(b, "type", None) == "tool_use"]
        if not tool_aufrufe:
            return

        ergebnisse = []
        for aufruf in tool_aufrufe:
            text = fuehre_werkzeug_aus(aufruf)
            ergebnisse.append({"type": "tool_result", "tool_use_id": aufruf.id, "content": text})
        st.session_state.messages.append({"role": "user", "content": ergebnisse})


def chat_eingabe(platzhalter="Deine Antwort …"):
    eingabe = st.chat_input(platzhalter)
    if eingabe:
        st.session_state.messages.append({"role": "user", "content": eingabe})
        with st.chat_message("user"):
            st.markdown(eingabe)
        with st.spinner("…"):
            fuehre_dialog_runde()
        st.rerun()


# =============================================================
#  Sitzungsspeicher
# =============================================================
for key, default in [
    ("phase", 0),
    ("messages", []),
    ("typ", None),
    ("optionen", []),
    ("gewichte", {}),
    ("nutzer_werte", {}),
    ("basis_ergebnis", None),
    ("sensitivitaet_ergebnis", None),
    ("robustheit", None),
    ("phase0_gestartet", False),
    ("phase3_gestartet", False),
    ("phase6_gestartet", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# =============================================================
#  KOPF + NAVIGATION
# =============================================================
st.title("🏭 Entscheidungsmodell: globale Produktionsnetzwerke")

with st.sidebar:
    st.subheader("Phasen")
    st.caption("Bereits erreichte Phasen sind anklickbar.")
    for i in range(ANZAHL_PHASEN):
        ist_aktuell = (i == st.session_state.phase)
        erreichbar = i <= st.session_state.phase or (i <= 2 and st.session_state.typ is not None)
        marker = "▶️" if ist_aktuell else ("✅" if i < st.session_state.phase else "▫️")
        if st.button(f"{marker} {PHASEN[i]['titel']}", key=f"nav_{i}",
                     disabled=not erreichbar or ist_aktuell, width="stretch"):
            st.session_state.phase = i
            st.rerun()
    st.divider()
    if st.button("🔁 Neue Analyse starten", width="stretch"):
        for k in list(st.session_state.keys()):
            st.session_state.pop(k, None)
        st.rerun()

PHASE = st.session_state.phase
if st.session_state.typ:
    st.caption(f"Szenario-Typ: **{st.session_state.typ}** | Optionen: **{', '.join(st.session_state.optionen)}**")


# =============================================================
#  AUTO-START-TRIGGER
# =============================================================
if PHASE == 0 and not st.session_state.phase0_gestartet:
    st.session_state.phase0_gestartet = True
    with st.spinner("Starte …"):
        st.session_state.messages.append({
            "role": "user",
            "content": AUTO_MARKER + " Starte Phase 0: Begruesse den Nutzer und erklaere das Vorgehen."
        })
        fuehre_dialog_runde()
    st.rerun()

if PHASE == 3 and not st.session_state.phase3_gestartet:
    st.session_state.phase3_gestartet = True
    with st.spinner("Prüfe Datenlage …"):
        st.session_state.messages.append({
            "role": "user",
            "content": AUTO_MARKER + " Starte Phase 3: Erklaere die Datenlage und frage die fehlenden Werte ab."
        })
        fuehre_dialog_runde()
    st.rerun()

if PHASE == 6 and not st.session_state.phase6_gestartet:
    if st.session_state.basis_ergebnis is None:
        st.warning("Es liegt noch kein Basis-Ergebnis vor. Bitte Phase 4 durchlaufen.")
        st.stop()
    st.session_state.phase6_gestartet = True
    with st.spinner("Erstelle die Zusammenfassung …"):
        st.session_state.messages.append({
            "role": "user",
            "content": AUTO_MARKER + " Starte Phase 6: Erstelle die Abschluss-Zusammenfassung."
        })
        fuehre_dialog_runde()
    st.rerun()


# =============================================================
#  CHATVERLAUF
# =============================================================
zeige_verlauf()


# =============================================================
#  OBERFLAECHE DER AKTUELLEN PHASE
# =============================================================
if PHASE == 0:
    st.divider()
    st.markdown("**Die Phasen im Überblick:**")
    st.dataframe([
        {"Phase": PHASEN[i]["titel"], "Was passiert": PHASEN[i]["kurz"]}
        for i in range(1, ANZAHL_PHASEN)
    ], width="stretch", hide_index=True)

if PHASE == 2:
    st.divider()
    st.subheader(PHASEN[2]["titel"])
    st.write(
        "Lege fest, wie wichtig dir die fünf Leistungsdimensionen für diese "
        "Entscheidung sind. Die Summe der Gewichtungen bleibt automatisch bei "
        "100 %. Ziehst du einen Regler hoch, passen sich die anderen Regler an."
    )
    zeige_gewichts_slider(ALLE_DIMENSIONEN)
    st.caption("Wenn du mit der Gewichtung fertig bist, schreibe unten im Chat z. B. »weiter«.")

if PHASE == 3:
    st.divider()
    st.subheader(PHASEN[3]["titel"])
    st.write(
        "In dieser Phase frage ich die Daten ab. Einige Werte kann ich bereits "
        "aus dem System ziehen; die restlichen Werte benötige ich von dir. "
        "Die Tabelle zeigt dir transparent, welche Werte bereits vorliegen und "
        "welche noch ergänzt werden müssen."
    )
    rohwerte, herkunft = baue_rohwerte()
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    zeilen = []
    for k in aktiv:
        zeile = {"Dimension": KPIS[k]["dimension"], "Kennzahl": k, "Einheit": KPIS[k]["einheit"]}
        for opt in st.session_state.optionen:
            if k in rohwerte.get(opt, {}):
                quelle = HERKUNFT_LABEL.get(herkunft[opt][k], "?")
                zeile[opt] = f"{rohwerte[opt][k]} ({quelle})"
            else:
                zeile[opt] = "❓"
        zeilen.append(zeile)
    st.dataframe(zeilen, width="stretch", hide_index=True)

if PHASE == 4:
    st.divider()
    st.subheader(PHASEN[4]["titel"])
    offen = offene_werte()
    if offen:
        st.warning("Es fehlen noch Werte (Phase 3): " + "; ".join(f"{o}: {', '.join(ks)}" for o, ks in offen.items()))
        st.stop()

    # Basis-Ergebnis bewusst einfrieren: Es geht spaeter in die PDF.
    if st.session_state.basis_ergebnis is None:
        st.session_state.basis_ergebnis = rechne()
    erg = st.session_state.basis_ergebnis

    st.markdown(
        "**Normierungsformel:** Normwert = (Istwert − Grenzwert) / "
        "(Zielwert − Grenzwert) × 100, gedeckelt auf 0–100. "
        "Die Richtung ergibt sich automatisch aus der Lage von Ziel- zu Grenzwert."
    )

    st.markdown("**Normwerte je Kennzahl (0–100):**")
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    zeilen = []
    for k in aktiv:
        zeile = {"Dimension": KPIS[k]["dimension"], "Kennzahl": k}
        for opt in st.session_state.optionen:
            zeile[opt] = erg["normwerte"].get(opt, {}).get(k, "—")
        zeilen.append(zeile)
    st.dataframe(zeilen, width="stretch", hide_index=True)

    st.markdown("**Dimensions-Scores** (Mittelwert der Normwerte je Dimension):")
    zeilen = []
    for d in ALLE_DIMENSIONEN:
        zeile = {"Dimension": d, "Gewicht": f"{erg['gewichte'].get(d, 0)*100:.0f} %"}
        for opt in st.session_state.optionen:
            zeile[opt] = erg["dim_scores"].get(opt, {}).get(d, "—")
        zeilen.append(zeile)
    st.dataframe(zeilen, width="stretch", hide_index=True)

    st.markdown("**Nutzwerte** (= Σ Gewicht × Dimensions-Score):")
    st.dataframe([
        {"Rang": erg["raenge"][o], "Option": o, "Nutzwert": erg["nutzwerte"][o]}
        for o in sorted(erg["nutzwerte"], key=erg["nutzwerte"].get, reverse=True)
    ], width="stretch", hide_index=True)
    st.info(f"Empfehlung nach initialer Gewichtung: **{erg['empfehlung']}**")
    st.caption("Wenn du zur Sensitivitätsanalyse wechseln möchtest, schreibe unten im Chat z. B. »weiter«.")

if PHASE == 5:
    st.divider()
    st.subheader(PHASEN[5]["titel"])
    if st.session_state.basis_ergebnis is None:
        st.warning("Es liegt noch kein Basis-Ergebnis vor. Bitte Phase 4 durchlaufen.")
        st.stop()

    st.write(
        "Verändere die Gewichtung und berechne das Ergebnis neu. So prüfst du, "
        "ob die Empfehlung stabil bleibt. Die ursprüngliche Gewichtung aus "
        "Phase 2 bleibt für die Ergebnis-PDF gespeichert."
    )

    # Sensitivitaetsanalyse startet mit der initialen Gewichtung.
    if "sensitivitaet_gewichte" not in st.session_state:
        st.session_state.sensitivitaet_gewichte = dict(st.session_state.basis_ergebnis["gewichte"])
        setze_slider_aus_gewichten(st.session_state.sensitivitaet_gewichte)

    st.session_state.gewichte = st.session_state.sensitivitaet_gewichte
    zeige_gewichts_slider(ALLE_DIMENSIONEN, ziel_key="sensitivitaet_gewichte")

    if st.button("🔄 Neu berechnen"):
        st.session_state.sensitivitaet_ergebnis = rechne_mit_gewichten(st.session_state.sensitivitaet_gewichte)
        st.rerun()

    erg = st.session_state.sensitivitaet_ergebnis or st.session_state.basis_ergebnis
    st.dataframe([
        {"Rang": erg["raenge"][o], "Option": o, "Nutzwert": erg["nutzwerte"][o]}
        for o in sorted(erg["nutzwerte"], key=erg["nutzwerte"].get, reverse=True)
    ], width="stretch", hide_index=True)
    st.info(f"Aktuelle Empfehlung im Sensitivitätstest: **{erg['empfehlung']}**")
    st.caption(
        "Wenn du mehrere Gewichtungen getestet hast, schreibe im Chat, ob du "
        "das Ergebnis als robust oder nicht robust bewertest. Diese Einschätzung "
        "wird in der Zusammenfassung dokumentiert."
    )

if PHASE == 6 and st.session_state.basis_ergebnis:
    st.divider()
    pdf_bytes = erstelle_ergebnis_pdf(
        st.session_state.basis_ergebnis,
        letzter_bot_text(),
        st.session_state.typ or "",
        st.session_state.optionen,
        KPIS,
        aktive_kennzahlen(MATRIX, st.session_state.typ) if st.session_state.typ else [],
        st.session_state.robustheit,
    )
    st.download_button("📄 Ergebnis-PDF herunterladen", data=pdf_bytes,
                       file_name="entscheidungsempfehlung.pdf",
                       mime="application/pdf")


# =============================================================
#  EINGABEZEILE
# =============================================================
chat_eingabe()
