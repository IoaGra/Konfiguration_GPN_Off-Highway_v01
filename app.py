# =============================================================
#  HAUPTANWENDUNG (Streamlit) - Version 6
# =============================================================
#  Entscheidungsassistent fuer die Konfiguration globaler
#  Produktionsnetzwerke (Off-Highway-Motorenbranche).
#
#  Neu in V6:
#   - 8 Phasen (0-7), dialoggefuehrt: der Bot erklaert, kuendigt
#     den naechsten Schritt an und schaltet die Phasen selbst
#     weiter (Werkzeug 'naechste_phase'). Erklaerungen zu
#     Szenarien/Dimensionen nur auf Nachfrage.
#   - Datengrundlage: daten.xlsx (Ziel-/Grenzwerte + Optionswerte,
#     fehlende Werte mit '/'), kennzahlen.xlsx,
#     szenario_kennzahl_matrix.xlsx.
#   - Normierung nach Ziel-/Grenzwert-Verfahren (0-100, gedeckelt):
#       Normwert = (Ist - Grenz) / (Ziel - Grenz) * 100
#   - 6 Leistungsdimensionen inkl. Interdependenzen.
#   - Auswahl von mindestens 2 Auspraegungen (z.B. Standorten).
#   - ALLE Berechnungen deterministisch in berechnung.py.
# =============================================================

import json
import streamlit as st
import anthropic

from berechnung import berechne_nutzwerte, normiere
from formeln import (FORMEL_KENNZAHLEN, berechne_formel_kennzahl,
                     formel_hinweis_fuer_prompt)
from daten import lade_daten, dimensionen_aus_kpis
from matrix import lade_matrix, aktive_kennzahlen
from szenarien import SZENARIO_BESCHREIBUNGEN
from dimensionen import DIMENSION_BESCHREIBUNGEN
from phasen import PHASEN, ANZAHL_PHASEN
from pdf_export import erstelle_ergebnis_pdf

# -------------------------------------------------------------
MODELL = "claude-sonnet-4-6"
MAX_TOKENS = 1600
HERKUNFT_LABEL = {"system": "aus System", "nutzer": "Nutzereingabe"}

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
    zusammen. Rueckgabe: (rohwerte, herkunft) je {option: {kennzahl: ...}}."""
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
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
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    rohwerte, _ = baue_rohwerte()
    offen = {}
    for opt in st.session_state.optionen:
        fehlt = [k for k in aktiv if k not in rohwerte[opt]]
        if fehlt:
            offen[opt] = fehlt
    return offen


def rechne():
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    rohwerte, herkunft = baue_rohwerte()
    erg = berechne_nutzwerte(rohwerte, aktiv, KPIS,
                             st.session_state.gewichte)
    erg["rohwerte"] = rohwerte
    erg["herkunft"] = herkunft
    return erg


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
        st.slider(d, min_value=0, max_value=100, key=f"w_{d}",
                  on_change=slider_geaendert, args=(d, dims))
    summe = sum(st.session_state[f"w_{d}"] for d in dims)
    st.write(f"**Summe:** {summe} %")


# =============================================================
#  SPRACHMODELL: System-Prompt + Werkzeuge
# =============================================================

def baue_system_prompt():
    phase = st.session_state.phase
    typ = st.session_state.typ

    szenario_namen = ", ".join(SZENARIO_TYPEN)
    options_namen = ", ".join(ALLE_OPTIONEN)
    dims = ", ".join(ALLE_DIMENSIONEN)

    kontext = ""
    if typ:
        aktiv = aktive_kennzahlen(MATRIX, typ)
        kontext += (f"\nGewaehlter Szenario-Typ: {typ}. "
                    f"Gewaehlte Optionen: {', '.join(st.session_state.optionen)}. "
                    f"Aktive Kennzahlen laut Matrix: {', '.join(aktiv)}.")
    if phase == 4 and typ:
        offen = offene_werte()
        if offen:
            kontext += ("\nFolgende Werte FEHLEN und muessen beim Nutzer "
                        "abgefragt werden: " +
                        "; ".join(f"{o}: {', '.join(ks)}" for o, ks in offen.items()) +
                        ".\nFuer Formel-Kennzahlen frage die Faktoren ab "
                        "(Berechnung erfolgt im Code):\n" +
                        formel_hinweis_fuer_prompt())
        else:
            kontext += "\nAlle Werte liegen vor."

    phasen_anweisung = {
        0: ("Begruesse den Nutzer herzlich und etwas ausfuehrlicher. Erklaere "
            "das Ziel (Szenarien systematisch vergleichen und eine begruendete "
            "Empfehlung ableiten) und gehe die Phasen 1-7 einzeln mit je einem "
            "Satz durch - die App zeigt zusaetzlich eine Uebersichtstabelle "
            "unter deiner Nachricht. Erklaere auch, dass der Nutzer jederzeit "
            "Fragen stellen kann. Frage am Ende, ob es losgehen kann. Wenn der "
            "Nutzer zustimmt, rufe 'naechste_phase' auf."),
        1: ("Nenne die verfuegbaren Szenario-Typen NUR mit Namen (keine "
            "Beschreibungen!) und biete an, einzelne auf Nachfrage zu "
            "erklaeren. Der Nutzer muss einen Typ und MINDESTENS ZWEI "
            "Optionen/Auspraegungen waehlen (verfuegbar: " + options_namen + "). "
            "'keine Änderung' ist die Referenz. Wenn beides klar ist, frage "
            "kurz, ob noch Fragen offen sind; danach rufe 'setze_szenarien' "
            "auf - das schaltet automatisch zu Phase 2."),
        2: ("Die App zeigt dem Nutzer bereits eine Tabelle der aktiven "
            "Kennzahlen. Fasse kurz zusammen (NICHT alle aufzaehlen), biete "
            "Erklaerungen zu Kennzahlen oder Leistungsdimensionen auf "
            "Nachfrage an, und kuendige an, dass als naechstes die Gewichtung "
            "folgt. Frage, ob es noch Fragen gibt; wenn der Nutzer bereit "
            "ist, rufe 'naechste_phase' auf."),
        3: ("Die Gewichtung laeuft ueber Schieberegler in der App. Du musst "
            "nichts abfragen. Beantworte Fragen zu den Dimensionen, falls "
            "gestellt."),
        4: ("Erklaere transparent: ein Teil der Daten liegt im System vor, "
            "die fehlenden fragst du jetzt ab. Frage die fehlenden Werte "
            "gezielt und einzeln ab (siehe Kontext). Bei Formel-Kennzahlen "
            "(z.B. Kapazitaetsauslastung, Qualitaetsrate) frage die im "
            "Kontext genannten FAKTOREN ab. Wenn du alle fehlenden Werte "
            "hast, rufe 'speichere_fehlende_werte' auf; gib Formel-"
            "Kennzahlen als Objekt mit den Faktor-Feldern an (z.B. "
            "{\"Qualitätsrate\": {\"gutteile\": 98500, \"gesamtproduktion\": "
            "100000}}). Frage anschliessend, ob noch Werte "
            "angepasst werden sollen. RECHNE NIEMALS SELBST - keine Scores, "
            "keine Normierungen, keine Mittelwerte. Alle Berechnungen "
            "erfolgen ausschliesslich im Code der Anwendung."),
        5: ("Die Berechnung wird in der App angezeigt. Beantworte Fragen "
            "dazu. Erklaere auf Wunsch die Normierungsformel: "
            "Normwert = (Ist - Grenzwert) / (Zielwert - Grenzwert) * 100, "
            "gedeckelt auf 0-100."),
        6: ("Die Sensitivitaetsanalyse laeuft ueber die Schieberegler. "
            "Beantworte Fragen zur Interpretation."),
        7: ("Erstelle die detaillierte Abschluss-Zusammenfassung entlang der "
            "Phasen: gewaehltes Szenario und Optionen, verwendete Kennzahlen, "
            "Gewichtung, Datenherkunft, Normierungsformel (mit Ziel- und "
            "Grenzwerten), Dimensions-Scores und Nutzwerte aus dem "
            "Ergebnis-Kontext, Empfehlung. Nutze Tabellen, wo sinnvoll. "
            "Verwende NUR die Zahlen aus dem Kontext - erfinde keine. "
            "Beende deine Antwort ZWINGEND mit diesen zwei klar markierten "
            "Abschnitten (je 3-6 Stichpunkte, jeder Stichpunkt beginnt mit "
            "'- '):\n"
            "ZUSAMMENFASSUNG:\n- ...\n"
            "WEITERE BETRACHTUNG:\n- ... (Aspekte, die das Modell nicht "
            "abdeckt, z.B. Einmalkosten der Umstellung, qualitative Risiken, "
            "Personal, Lieferketten-Resilienz)"),
    }[phase]

    ergebnis_kontext = ""
    if phase == 7 and st.session_state.letztes_ergebnis:
        erg = st.session_state.letztes_ergebnis
        kompakt = {
            "gewichte": erg["gewichte"],
            "dim_scores": erg["dim_scores"],
            "nutzwerte": erg["nutzwerte"],
            "raenge": erg["raenge"],
            "empfehlung": erg["empfehlung"],
            "normwerte": erg["normwerte"],
            "herkunft": erg["herkunft"],
        }
        ergebnis_kontext = ("\nERGEBNIS (deterministisch berechnet):\n" +
                            json.dumps(kompakt, ensure_ascii=False))

    return f"""Du bist ein Entscheidungsassistent fuer die Konfiguration \
globaler Produktionsnetzwerke in der Off-Highway-Motorenbranche. Du fuehrst \
den Nutzer dialogorientiert durch 7 Phasen (plus Einstieg), erklaerst, was \
als naechstes passiert, und holst den Nutzer aktiv ab.

Verfuegbare Szenario-Typen: {szenario_namen}
Verfuegbare Optionen/Auspraegungen: {options_namen}
Leistungsdimensionen: {dims}

GRUNDREGELN:
- Jede numerische Berechnung erfolgt zwingend im Anwendungscode. Es ist dir \
verboten, Scores, Nutzwerte, Normierungen, Gewichtungen, Mittelwerte oder \
Rankings selbst zu berechnen oder zu schaetzen.
- Bleibe in der aktuellen Phase, springe nicht voraus. Fasse am Ende einer \
Phase kurz zusammen und kuendige die naechste an.
- Frage VOR jedem Phasenwechsel: Gibt es noch Fragen oder muessen Werte \
angepasst werden? Wechsle erst nach Bestaetigung des Nutzers.
- Erklaerungen zu Szenarien und Leistungsdimensionen NUR auf Nachfrage geben \
(Beschreibungen stehen dir unten zur Verfuegung).
- Nutze Tabellen, wo sinnvoll. Frage fehlende Informationen gezielt nach.
- Nutze ausschliesslich das Wissen aus diesem Prompt und dem Gespraech.
- Antworte auf Deutsch, freundlich, knapp und im Dialog.

AKTUELLE PHASE {phase}: {PHASEN[phase]['titel']}
{phasen_anweisung}
{kontext}{ergebnis_kontext}

BESCHREIBUNGEN (nur auf Nachfrage verwenden):
Szenarien: {json.dumps(SZENARIO_BESCHREIBUNGEN, ensure_ascii=False)}
Leistungsdimensionen: {json.dumps(DIMENSION_BESCHREIBUNGEN, ensure_ascii=False)}"""


def tool_definitionen():
    werkzeuge = [{
        "name": "naechste_phase",
        "description": ("Schaltet zur naechsten Phase weiter. Aufrufen, wenn "
                        "die aktuelle Phase abgeschlossen ist und der Nutzer "
                        "bereit ist."),
        "input_schema": {"type": "object", "properties": {}},
    }]
    if st.session_state.phase == 1:
        werkzeuge.append({
            "name": "setze_szenarien",
            "description": ("Legt Szenario-Typ und die gewaehlten Optionen "
                            "(mind. 2) fest und schaltet zu Phase 2."),
            "input_schema": {
                "type": "object",
                "properties": {
                    "typ": {"type": "string",
                            "description": "Einer der Szenario-Typen (exakter Name)."},
                    "optionen": {"type": "array", "items": {"type": "string"},
                                 "description": "Mind. 2 der verfuegbaren Optionen "
                                                "(exakte Namen)."},
                },
                "required": ["typ", "optionen"],
            },
        })
    if st.session_state.phase == 4:
        werkzeuge.append({
            "name": "speichere_fehlende_werte",
            "description": ("Speichert die vom Nutzer abgefragten fehlenden "
                            "Werte. Formel-Kennzahlen als Faktor-Objekt "
                            "angeben."),
            "input_schema": {
                "type": "object",
                "properties": {
                    "werte": {
                        "type": "object",
                        "description": ('{Option: {Kennzahl: Zahl ODER '
                                        'Faktor-Objekt}}. Formel-Kennzahlen '
                                        'als Objekt mit den definierten '
                                        'Faktor-Feldern, z.B. '
                                        '{"Qualitätsrate": {"gutteile": 98500, '
                                        '"gesamtproduktion": 100000}}.'),
                    }
                },
                "required": ["werte"],
            },
        })
    return werkzeuge


def fuehre_werkzeug_aus(aufruf):
    """Fuehrt einen Werkzeugaufruf robust aus. Gibt den tool_result-Text zurueck."""
    if aufruf.name == "naechste_phase":
        if st.session_state.phase < ANZAHL_PHASEN - 1:
            st.session_state.phase += 1
        return f"Phase gewechselt. Aktuelle Phase: {st.session_state.phase}."

    if aufruf.name == "setze_szenarien":
        typ = (aufruf.input.get("typ") or "").strip()
        optionen = aufruf.input.get("optionen") or []
        if typ not in SZENARIO_TYPEN:
            return (f"Unbekannter Szenario-Typ '{typ}'. Verfuegbar: "
                    f"{', '.join(SZENARIO_TYPEN)}. Bitte erneut klaeren.")
        gueltige = [o for o in optionen if o in ALLE_OPTIONEN]
        if len(gueltige) < 2:
            return (f"Mindestens 2 gueltige Optionen noetig. Verfuegbar: "
                    f"{', '.join(ALLE_OPTIONEN)}. Bitte erneut klaeren.")
        st.session_state.typ = typ
        st.session_state.optionen = gueltige
        st.session_state.gewichte = {d: 1.0 / len(ALLE_DIMENSIONEN)
                                     for d in ALLE_DIMENSIONEN}
        st.session_state.phase = 2
        return (f"Szenario gesetzt: {typ} mit Optionen {', '.join(gueltige)}. "
                "Phase 2 ist aktiv; die Kennzahlen-Tabelle wird dem Nutzer "
                "angezeigt.")

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
                if isinstance(v, dict):
                    # Formel-Kennzahl: aus Faktoren deterministisch berechnen
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
            return ("Gespeichert: " + "; ".join(gespeichert) +
                    ". Es fehlen noch: " +
                    "; ".join(f"{o}: {', '.join(ks)}" for o, ks in offen.items()) +
                    ". Bitte weiter abfragen.")
        return ("Gespeichert: " + "; ".join(gespeichert) +
                ". Alle Werte liegen vor. Fasse kurz zusammen und rufe dann "
                "'naechste_phase' auf.")

    return "Unbekanntes Werkzeug."


def fuehre_dialog_runde():
    while True:
        try:
            antwort = client.messages.create(
                model=MODELL, max_tokens=MAX_TOKENS,
                system=baue_system_prompt(),
                tools=tool_definitionen(),
                messages=st.session_state.messages)
        except Exception as e:
            st.error("Verbindung zum Sprachmodell fehlgeschlagen. Bitte Seite "
                     "neu laden und erneut versuchen. (Details: "
                     f"{type(e).__name__})")
            return
        st.session_state.messages.append(
            {"role": "assistant", "content": antwort.content})
        tool_aufrufe = [b for b in antwort.content
                        if getattr(b, "type", None) == "tool_use"]
        if not tool_aufrufe:
            return
        ergebnisse = []
        for aufruf in tool_aufrufe:
            text = fuehre_werkzeug_aus(aufruf)
            ergebnisse.append({"type": "tool_result",
                               "tool_use_id": aufruf.id, "content": text})
        st.session_state.messages.append({"role": "user", "content": ergebnisse})


def _block_attr(b, name):
    return b.get(name) if isinstance(b, dict) else getattr(b, name, None)


AUTO_MARKER = "[AUTO]"   # interne Steuer-Nachrichten, im Chat unsichtbar


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
for key, default in [("phase", 0), ("messages", []), ("typ", None),
                     ("optionen", []), ("gewichte", {}),
                     ("nutzer_werte", {}), ("letztes_ergebnis", None),
                     ("phase0_gestartet", False), ("phase7_gestartet", False)]:
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
        erreichbar = i <= st.session_state.phase or (
            i <= 2 and st.session_state.typ is not None)
        marker = "▶️" if ist_aktuell else ("✅" if i < st.session_state.phase else "▫️")
        if st.button(f"{marker} {PHASEN[i]['titel']}", key=f"nav_{i}",
                     disabled=not erreichbar or ist_aktuell,
                     width="stretch"):
            st.session_state.phase = i
            st.rerun()
    st.divider()
    if st.button("🔁 Neue Analyse starten", width="stretch"):
        for k in list(st.session_state.keys()):
            st.session_state.pop(k, None)
        st.rerun()

PHASE = st.session_state.phase
if st.session_state.typ:
    st.caption(f"Szenario-Typ: **{st.session_state.typ}** | "
               f"Optionen: **{', '.join(st.session_state.optionen)}**")

# =============================================================
#  PHASEN-LOGIK
#  Renderreihenfolge (chronologisch):
#   1) Auto-Start-Trigger (unsichtbar, AUTO-Nachrichten)
#   2) Chatverlauf
#   3) Oberflaeche der AKTUELLEN Phase (Tabellen, Regler, Knoepfe)
#   4) Eingabezeile ganz unten
# =============================================================

# ---- 1) Auto-Start-Trigger (keine UI) ----
if PHASE == 0 and not st.session_state.phase0_gestartet:
    st.session_state.phase0_gestartet = True
    with st.spinner("Starte …"):
        st.session_state.messages.append(
            {"role": "user",
             "content": AUTO_MARKER + " Starte Phase 0: Begruesse den Nutzer "
                        "ausfuehrlich und erklaere das Vorgehen."})
        fuehre_dialog_runde()
    st.rerun()

if PHASE == 4 and "phase4_gestartet" not in st.session_state:
    st.session_state.phase4_gestartet = True
    with st.spinner("Prüfe Datenlage …"):
        st.session_state.messages.append(
            {"role": "user",
             "content": AUTO_MARKER + " Starte Phase 4: Erklaere die Datenlage "
                        "und frage die fehlenden Werte ab."})
        fuehre_dialog_runde()
    st.rerun()

if PHASE == 7 and not st.session_state.phase7_gestartet:
    if st.session_state.letztes_ergebnis is None:
        st.warning("Es liegt noch kein Ergebnis vor. Bitte Phase 5 durchlaufen.")
        st.stop()
    st.session_state.phase7_gestartet = True
    with st.spinner("Erstelle die Zusammenfassung …"):
        st.session_state.messages.append(
            {"role": "user",
             "content": AUTO_MARKER + " Starte Phase 7: Erstelle die "
                        "detaillierte Zusammenfassung entlang der Phasen."})
        fuehre_dialog_runde()
    st.rerun()

# ---- 2) Chatverlauf (immer zuerst sichtbar) ----
zeige_verlauf()

# ---- 3) Oberflaeche der aktuellen Phase ----
if PHASE == 0:
    st.divider()
    st.markdown("**Die Phasen im Überblick:**")
    st.dataframe([{"Phase": PHASEN[i]["titel"], "Was passiert": PHASEN[i]["kurz"]}
                  for i in range(1, ANZAHL_PHASEN)],
                 width="stretch", hide_index=True)

if PHASE == 2 and st.session_state.typ:
    st.divider()
    st.subheader(PHASEN[2]["titel"])
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    zeilen = [{"Leistungsdimension": KPIS[k]["dimension"],
               "Kennzahl": k,
               "Formelzeichen": KPIS[k].get("formelzeichen", ""),
               "Einheit": KPIS[k]["einheit"],
               "Zielwert": KPIS[k]["zielwert"],
               "Grenzwert": KPIS[k]["grenzwert"]} for k in aktiv]
    st.dataframe(zeilen, width="stretch", hide_index=True)
    st.caption("Diese Kennzahlen werden laut Szenario-Kennzahl-Matrix "
               "verglichen. Frage im Chat nach, wenn du eine Erklärung "
               "möchtest — oder schreibe »weiter«, um zur Gewichtung zu gehen.")

if PHASE == 3:
    st.divider()
    st.subheader(PHASEN[3]["titel"])
    st.write("Lege fest, wie wichtig dir die Leistungsdimensionen sind. "
             "Ziehst du einen Regler hoch, passen sich die anderen automatisch "
             "an (Summe immer 100 %). Frage im Chat nach, wenn du eine "
             "Erklärung zu einer Dimension möchtest.")
    zeige_gewichts_slider(ALLE_DIMENSIONEN)
    st.caption("Gibt es noch Fragen oder möchtest du Werte anpassen? "
               "Sonst geht es weiter zur Datenabfrage.")
    if st.button("Gewichtung übernehmen → weiter zur Datenabfrage ▶️"):
        st.session_state.phase = 4
        st.rerun()

if PHASE == 4:
    st.divider()
    st.subheader(PHASEN[4]["titel"])
    rohwerte, herkunft = baue_rohwerte()
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    offen = offene_werte()
    st.markdown("**Datenübersicht** (Herkunft je Wert; ❓ = wird noch abgefragt)")
    zeilen = []
    for k in aktiv:
        zeile = {"Dimension": KPIS[k]["dimension"], "Kennzahl": k,
                 "Einheit": KPIS[k]["einheit"]}
        for opt in st.session_state.optionen:
            if k in rohwerte[opt]:
                quelle = HERKUNFT_LABEL.get(herkunft[opt][k], "?")
                zeile[opt] = f"{rohwerte[opt][k]} ({quelle})"
            else:
                zeile[opt] = "❓"
        zeilen.append(zeile)
    st.dataframe(zeilen, width="stretch", hide_index=True)

    if not offen:
        st.caption("Alle Werte liegen vor. Gibt es noch Fragen oder müssen "
                   "Werte angepasst werden? Sonst weiter zur Berechnung.")
        if st.button("Weiter zur Berechnung ▶️"):
            st.session_state.phase = 5
            st.rerun()

if PHASE == 5:
    st.divider()
    st.subheader(PHASEN[5]["titel"])
    offen = offene_werte()
    if offen:
        st.warning("Es fehlen noch Werte (Phase 4): " +
                   "; ".join(f"{o}: {', '.join(ks)}" for o, ks in offen.items()))
        st.stop()

    erg = rechne()
    st.session_state.letztes_ergebnis = erg

    st.markdown("**Normierungsformel:** Normwert = (Istwert − Grenzwert) / "
                "(Zielwert − Grenzwert) × 100, gedeckelt auf 0–100. "
                "Die Richtung (höher/niedriger besser) ergibt sich automatisch "
                "aus der Lage von Ziel- zu Grenzwert.")

    st.markdown("**Normwerte je Kennzahl (0–100):**")
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    zeilen = []
    for k in aktiv:
        zeile = {"Dimension": KPIS[k]["dimension"], "Kennzahl": k}
        for opt in st.session_state.optionen:
            zeile[opt] = erg["normwerte"][opt].get(k, "—")
        zeilen.append(zeile)
    st.dataframe(zeilen, width="stretch", hide_index=True)

    st.markdown("**Dimensions-Scores** (Mittelwert der Normwerte je Dimension):")
    zeilen = []
    for d in ALLE_DIMENSIONEN:
        zeile = {"Dimension": d, "Gewicht": f"{erg['gewichte'].get(d,0)*100:.0f} %"}
        for opt in st.session_state.optionen:
            zeile[opt] = erg["dim_scores"][opt].get(d, "—")
        zeilen.append(zeile)
    st.dataframe(zeilen, width="stretch", hide_index=True)

    st.markdown("**Nutzwerte** (= Σ Gewicht × Dimensions-Score):")
    st.dataframe(
        [{"Rang": erg["raenge"][o], "Option": o, "Nutzwert": erg["nutzwerte"][o]}
         for o in sorted(erg["nutzwerte"], key=erg["nutzwerte"].get, reverse=True)],
        width="stretch", hide_index=True)
    st.info(f"Empfehlung nach aktueller Gewichtung: **{erg['empfehlung']}**")

    st.caption("Gibt es noch Fragen zur Berechnung? Sonst weiter zur "
               "Sensitivitätsanalyse.")
    if st.button("Weiter zur Sensitivitätsanalyse ▶️"):
        st.session_state.phase = 6
        st.rerun()

if PHASE == 6:
    st.divider()
    st.subheader(PHASEN[6]["titel"])
    st.write("Verändere die Gewichtung und beobachte, wie sich die Rangfolge "
             "verschiebt. So prüfst du die Robustheit der Empfehlung.")
    zeige_gewichts_slider(ALLE_DIMENSIONEN)
    if st.button("🔄 Neu berechnen"):
        st.session_state.letztes_ergebnis = rechne()
        st.rerun()
    erg = st.session_state.letztes_ergebnis
    if erg:
        st.dataframe(
            [{"Rang": erg["raenge"][o], "Option": o, "Nutzwert": erg["nutzwerte"][o]}
             for o in sorted(erg["nutzwerte"], key=erg["nutzwerte"].get, reverse=True)],
            width="stretch", hide_index=True)
        st.info(f"Empfehlung: **{erg['empfehlung']}**")
    st.caption("Gibt es noch Fragen oder möchtest du weitere Gewichtungen "
               "ausprobieren? Sonst weiter zur Zusammenfassung.")
    if st.button("Abschließen → Zusammenfassung ▶️"):
        st.session_state.phase = 7
        st.rerun()

if PHASE == 7 and st.session_state.letztes_ergebnis:
    st.divider()
    pdf_bytes = erstelle_ergebnis_pdf(
        st.session_state.letztes_ergebnis,
        letzter_bot_text(),
        st.session_state.typ or "",
        st.session_state.optionen,
        KPIS,
        aktive_kennzahlen(MATRIX, st.session_state.typ) if st.session_state.typ else [],
    )
    st.download_button("📄 Ergebnis-PDF herunterladen", data=pdf_bytes,
                       file_name="entscheidungsempfehlung.pdf",
                       mime="application/pdf")

# ---- 4) Eingabezeile (ganz unten) ----
chat_eingabe()
