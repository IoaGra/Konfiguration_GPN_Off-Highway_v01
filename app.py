# =============================================================
# HAUPTANWENDUNG (Streamlit) - validierungsorientierte Version
# =============================================================
# Entscheidungsassistent fuer die Konfiguration globaler
# Produktionsnetzwerke in der Off-Highway-Motorenbranche.
#
# Grundprinzip:
# - Claude fuehrt den Dialog und steuert die Phasen.
# - Alle Berechnungen erfolgen deterministisch im Python-Code.
# - Die Kennzahlenauswahl erfolgt im Hintergrund ueber die Matrix.
# - Die Ergebnis-PDF dokumentiert die initiale Gewichtung.
# =============================================================

import json
from typing import Optional

import anthropic
import streamlit as st

from berechnung import berechne_nutzwerte
from daten import lade_daten, dimensionen_aus_kpis
from dimensionen import DIMENSION_BESCHREIBUNGEN
from formeln import (
    berechne_formel_kennzahl,
    formel_beispiele_fuer_ui,
    formel_hinweis_fuer_prompt,
    ist_formel_kennzahl,
)
from matrix import aktive_kennzahlen, lade_matrix
from pdf_export import erstelle_ergebnis_pdf
from phasen import ANZAHL_PHASEN, PHASEN
from szenarien import SZENARIO_BESCHREIBUNGEN

# -------------------------------------------------------------
# Modell und Darstellung
# -------------------------------------------------------------
MODELL = st.secrets.get("CLAUDE_MODEL", "claude-opus-4-8")
MAX_TOKENS = 850
HERKUNFT_LABEL = {"system": "Systemwert", "nutzer": "Nutzereingabe"}
AUTO_MARKER = "[AUTO]"
ZUSAETZLICHE_OPTIONEN = ["Standort C"]

DEFAULT_GEWICHTE = {
    "Effizienz": 0.20,
    "Qualität": 0.20,
    "Zeit": 0.20,
    "Flexibilität": 0.20,
    "Ökologische Nachhaltigkeit": 0.20,
}

st.set_page_config(
    page_title="Konfiguration globaler Produktionsnetzwerke",
    layout="wide",
)

# Zusaetzlich zur Streamlit-Dark-Theme-Konfiguration wird die Oberflaeche
# hier einheitlich schwarz, weiss und blau gestaltet.
st.markdown(
    """
    <style>
    :root {
        --app-bg: #05070b;
        --panel-bg: #0b111a;
        --panel-bg-2: #101925;
        --text: #ffffff;
        --accent: #2f81f7;
        --accent-hover: #4c96ff;
        --border: #27405e;
    }

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"] {
        background: var(--app-bg) !important;
        color: var(--text) !important;
    }

    [data-testid="stSidebar"] {
        background: var(--panel-bg) !important;
        border-right: 1px solid var(--border);
    }

    [data-testid="stSidebar"] *,
    .stApp p,
    .stApp span,
    .stApp label,
    .stApp li,
    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp h5,
    .stApp h6,
    .stMarkdown,
    [data-testid="stText"] {
        color: var(--text) !important;
    }

    [data-testid="stChatMessage"] {
        background: var(--panel-bg) !important;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.25rem 0.75rem;
        margin-bottom: 0.55rem;
    }

    .stButton > button,
    .stDownloadButton > button {
        background: var(--panel-bg-2) !important;
        color: var(--text) !important;
        border: 1px solid var(--accent) !important;
        border-radius: 7px !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: var(--accent) !important;
        color: var(--text) !important;
    }

    .stButton > button:disabled {
        color: var(--text) !important;
        opacity: 1 !important;
        border-color: var(--border) !important;
    }

    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] input {
        color: var(--text) !important;
        background: var(--panel-bg) !important;
    }

    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        border: 1px solid var(--border);
        border-radius: 7px;
        overflow: hidden;
    }

    [data-baseweb="slider"] div[role="slider"] {
        background-color: var(--accent) !important;
    }

    hr {
        border-color: var(--border) !important;
    }

    a {
        color: var(--accent-hover) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

try:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    st.error(
        "Kein API-Schlüssel gefunden. Bitte hinterlegen Sie in den "
        "App-Einstellungen unter 'Secrets' den Eintrag ANTHROPIC_API_KEY."
    )
    st.stop()


# -------------------------------------------------------------
# Statische Daten
# -------------------------------------------------------------
@st.cache_data
def _lade_alles():
    kpis, optionen, werte, fehlend = lade_daten("daten.xlsx")
    typen, mat = lade_matrix("szenario_kennzahl_matrix.xlsx")
    return kpis, optionen, werte, fehlend, typen, mat


KPIS, EXCEL_OPTIONEN, SYSTEM_WERTE, FEHLEND, SZENARIO_TYPEN, MATRIX = _lade_alles()
ALLE_DIMENSIONEN = dimensionen_aus_kpis(KPIS)
VERFUEGBARE_OPTIONEN = list(dict.fromkeys(EXCEL_OPTIONEN + ZUSAETZLICHE_OPTIONEN))


# =============================================================
# HILFSFUNKTIONEN
# =============================================================
def baue_rohwerte():
    """Fuegt System- und Nutzerwerte fuer die gewaehlten Optionen zusammen."""
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
    """Ermittelt noch fehlende aktive Kennzahlen je gewaehlter Option."""
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
        st.slider(
            d,
            min_value=0,
            max_value=100,
            key=f"w_{d}",
            on_change=slider_geaendert,
            args=(d, dims, ziel_key),
        )
    summe = sum(st.session_state[f"w_{d}"] for d in dims)
    st.markdown(f"**Summe der Gewichtungen: {summe} %**")


def setze_slider_aus_gewichten(gewichte):
    for d in ALLE_DIMENSIONEN:
        st.session_state[f"w_{d}"] = round(gewichte.get(d, 0) * 100)


def initiale_gewichte():
    vorhandene = {d: DEFAULT_GEWICHTE.get(d, 0.0) for d in ALLE_DIMENSIONEN}
    summe = sum(vorhandene.values())
    if summe <= 0:
        return {d: 1.0 / len(ALLE_DIMENSIONEN) for d in ALLE_DIMENSIONEN}
    return {d: vorhandene[d] / summe for d in ALLE_DIMENSIONEN}


def _block_attr(block, name):
    return block.get(name) if isinstance(block, dict) else getattr(block, name, None)


def _index_letzte_assistentennachricht() -> Optional[int]:
    for i in range(len(st.session_state.messages) - 1, -1, -1):
        m = st.session_state.messages[i]
        if m["role"] == "assistant" and isinstance(m["content"], list):
            if any(_block_attr(b, "type") == "text" for b in m["content"]):
                return i
    return None


def zeige_verlauf(letzte_assistentenantwort_auslassen=False):
    auslassen = _index_letzte_assistentennachricht() if letzte_assistentenantwort_auslassen else None
    for i, m in enumerate(st.session_state.messages):
        if i == auslassen:
            continue
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
            texte = [
                _block_attr(b, "text")
                for b in m["content"]
                if _block_attr(b, "type") == "text"
            ]
            texte = [t for t in texte if t]
            if texte:
                return "\n".join(texte)
    return ""


def zeige_aktuellen_bot_text():
    text = letzter_bot_text()
    if text:
        with st.chat_message("assistant"):
            st.markdown(text)


def datenuebersicht():
    rohwerte, herkunft = baue_rohwerte()
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    zeilen = []
    for k in aktiv:
        zeile = {
            "Leistungsdimension": KPIS[k]["dimension"],
            "Kennzahl": k,
            "Einheit": KPIS[k]["einheit"],
        }
        for opt in st.session_state.optionen:
            if k in rohwerte.get(opt, {}):
                quelle = HERKUNFT_LABEL.get(herkunft[opt][k], "Unbekannt")
                zeile[opt] = f"{rohwerte[opt][k]} ({quelle})"
            else:
                zeile[opt] = "Fehlender Wert"
        zeilen.append(zeile)
    return zeilen


# =============================================================
# SPRACHMODELL: SYSTEM-PROMPT UND WERKZEUGE
# =============================================================
def _kompakte_beschreibungen():
    if st.session_state.phase not in (1, 2):
        return ""
    return (
        "\nBeschreibungen der Szenarien: "
        + json.dumps(SZENARIO_BESCHREIBUNGEN, ensure_ascii=False)
        + "\nBeschreibungen der Leistungsdimensionen: "
        + json.dumps(DIMENSION_BESCHREIBUNGEN, ensure_ascii=False)
    )


def baue_system_prompt():
    phase = st.session_state.phase
    typ = st.session_state.typ
    szenario_namen = ", ".join(SZENARIO_TYPEN)
    options_namen = ", ".join(VERFUEGBARE_OPTIONEN)
    dims = ", ".join(ALLE_DIMENSIONEN)

    kontext = ""
    if typ:
        aktiv = aktive_kennzahlen(MATRIX, typ)
        kontext += (
            f"\nAusgewählter Szenario-Typ: {typ}. "
            f"Betrachtete Baureihe: {st.session_state.baureihe or 'nicht angegeben'}. "
            f"Gewählte Optionen: {', '.join(st.session_state.optionen)}. "
            f"Aktive Kennzahlen: {', '.join(aktiv)}."
        )

    if phase == 3 and typ:
        offen = offene_werte()
        if offen:
            kontext += (
                "\nNoch fehlende Werte: "
                + "; ".join(f"{o}: {', '.join(ks)}" for o, ks in offen.items())
                + "\nHinweise zur Abfrage:\n"
                + formel_hinweis_fuer_prompt(offen)
            )
        else:
            kontext += "\nAlle erforderlichen Werte liegen vor."

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
                "\nInitiale Empfehlung: "
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
            kontext += (
                "\nLetztes Ergebnis der Sensitivitätsanalyse: "
                + json.dumps(kompakt, ensure_ascii=False)
            )

    if phase == 6 and st.session_state.basis_ergebnis:
        erg = st.session_state.basis_ergebnis
        kompakt = {
            "baureihe": st.session_state.baureihe,
            "gewichte": erg["gewichte"],
            "dim_scores": erg["dim_scores"],
            "nutzwerte": erg["nutzwerte"],
            "raenge": erg["raenge"],
            "empfehlung": erg["empfehlung"],
            "normwerte": erg["normwerte"],
            "robustheit": st.session_state.robustheit,
        }
        kontext += (
            "\nErgebnis für die Abschlusszusammenfassung: "
            + json.dumps(kompakt, ensure_ascii=False)
        )

    phasen_anweisung = {
        0: (
            "Begrüßen Sie die nutzende Person professionell. Erklären Sie in "
            "wenigen Sätzen, dass die Anwendung durch Szenarioauswahl, "
            "Gewichtung, Datenabfrage, Berechnung, Sensitivitätsanalyse und "
            "Zusammenfassung führt. Fragen Sie anschließend, ob begonnen "
            "werden kann. Bei Zustimmung rufen Sie naechste_phase auf."
        ),
        1: (
            "Nennen Sie zunächst ausschließlich die verfügbaren Szenario-Typen. "
            "Nennen Sie zu diesem Zeitpunkt noch keine Standorte. Nachdem ein "
            "Szenario-Typ gewählt wurde, fragen Sie bei einer Verlagerung zuerst, "
            "welche Baureihe verlagert werden soll. Nennen Sie danach die "
            f"möglichen Zielstandorte {options_namen} und fragen Sie, welche "
            "mindestens zwei Standorte verglichen werden sollen. Standort C muss "
            "als mögliche Auswahl angeboten werden. Sobald Szenario-Typ, "
            "Baureihe und Optionen eindeutig feststehen, rufen Sie "
            "setze_szenarien auf."
        ),
        2: (
            "Die Gewichtung erfolgt über die Schieberegler. Erläutern Sie die "
            "Leistungsdimensionen nur auf Nachfrage. Sobald die nutzende Person "
            "schriftlich bestätigt, dass die Gewichtung abgeschlossen ist, "
            "rufen Sie naechste_phase auf."
        ),
        3: (
            "Die Anwendung zeigt bereits eine Erläuterung und die Datentabelle. "
            "Wiederholen Sie diese Inhalte nicht. Fragen Sie pro Antwort genau "
            "einen fehlenden Wert in einem vollständigen Satz ab. Verwenden Sie "
            "für Rückfragen keine Aufzählungen. Bei Formel-Kennzahlen fragen Sie "
            "nur die vorgegebenen Eingabefaktoren ab und rufen danach "
            "speichere_fehlende_werte auf. Führen Sie selbst keine Rechnung aus. "
            "Wenn alle Werte vorliegen, fragen Sie in einem vollständigen Satz, "
            "ob die ausgefüllte Tabelle korrekt ist und mit der Berechnung "
            "fortgefahren werden kann. Wechseln Sie erst nach Bestätigung mit "
            "naechste_phase."
        ),
        4: (
            "Die Berechnung wird vollständig in der Anwendung dargestellt. "
            "Beantworten Sie fachliche Rückfragen in professionellem Fließtext. "
            "Sobald die nutzende Person fortfahren möchte, rufen Sie "
            "naechste_phase auf."
        ),
        5: (
            "Die nutzende Person variiert die Gewichtungen und berechnet das "
            "Ergebnis erneut. Bitten Sie anschließend in einem vollständigen "
            "Satz um die Einschätzung, ob das Ergebnis robust oder nicht robust "
            "ist. Sobald diese Einschätzung vorliegt, rufen Sie "
            "speichere_robustheit auf."
        ),
        6: (
            "Formulieren Sie eine professionelle textliche Zusammenfassung in "
            "drei klar voneinander getrennten Absätzen ohne Stichpunkte. Der "
            "erste Absatz beschreibt das Vorgehen. Der zweite Absatz erläutert "
            "die Empfehlung anhand der Nutzwerte, Gewichtungen und wichtigsten "
            "Unterschiede der Leistungsdimensionen. Der dritte Absatz ordnet die "
            "Robustheitsbewertung ein und weist bei einer Produktionsverlagerung "
            "darauf hin, dass auch Auswirkungen auf den Ursprungsstandort zu "
            "berücksichtigen sind. Verwenden Sie ausschließlich Zahlen aus dem "
            "Kontext."
        ),
    }[phase]

    return f"""Sie sind ein professioneller Entscheidungsassistent für die Konfiguration globaler Produktionsnetzwerke in der Off-Highway-Motorenbranche.

Verfügbare Szenario-Typen: {szenario_namen}
Leistungsdimensionen: {dims}

Verbindliche Regeln:
- Sprechen Sie die nutzende Person konsequent mit "Sie" an.
- Verwenden Sie keine Emojis.
- Schreiben Sie professionell, sachlich und präzise.
- Beantworten Sie Rückfragen ausschließlich als Fließtext und nicht als Stichpunkte.
- Alle numerischen Berechnungen erfolgen ausschließlich im Anwendungscode.
- Berechnen oder schätzen Sie keine Scores, Nutzwerte, Normierungen, Mittelwerte oder Rangfolgen.
- Bleiben Sie in der aktuellen Phase.
- Erklären Sie Szenarien und Leistungsdimensionen nur auf Nachfrage.
- Fragen Sie fehlende Informationen einzeln und eindeutig ab.

Aktuelle Phase {phase}: {PHASEN[phase]['titel']}
{phasen_anweisung}
{kontext}
{_kompakte_beschreibungen()}
"""


def tool_definitionen():
    werkzeuge = [
        {
            "name": "naechste_phase",
            "description": "Schaltet zur nächsten Phase weiter.",
            "input_schema": {"type": "object", "properties": {}},
        }
    ]

    if st.session_state.phase == 1:
        werkzeuge.append(
            {
                "name": "setze_szenarien",
                "description": (
                    "Legt Szenario-Typ, betroffene Baureihe und Optionen fest "
                    "und schaltet zur Gewichtung."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "typ": {"type": "string"},
                        "baureihe": {
                            "type": "string",
                            "description": "Betroffene Baureihe, zum Beispiel Baureihe 2.",
                        },
                        "optionen": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["typ", "baureihe", "optionen"],
                },
            }
        )

    if st.session_state.phase == 3:
        werkzeuge.append(
            {
                "name": "speichere_fehlende_werte",
                "description": (
                    "Speichert fehlende Werte. Formel-Kennzahlen werden als "
                    "Faktor-Objekt übergeben."
                ),
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
            }
        )

    if st.session_state.phase == 5:
        werkzeuge.append(
            {
                "name": "speichere_robustheit",
                "description": (
                    "Speichert die Robustheitsbewertung nach der "
                    "Sensitivitätsanalyse."
                ),
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
            }
        )

    return werkzeuge


def fuehre_werkzeug_aus(aufruf):
    if aufruf.name == "naechste_phase":
        if st.session_state.phase < ANZAHL_PHASEN - 1:
            st.session_state.phase += 1
        # Die laufende Dialogrunde erzeugt bereits die erste Antwort der neuen
        # Phase. Die Auto-Trigger dürfen diese Antwort daher nicht duplizieren.
        if st.session_state.phase == 3:
            st.session_state.phase3_gestartet = True
        if st.session_state.phase == 6:
            st.session_state.phase6_gestartet = True
        return f"Phase gewechselt. Aktuelle Phase: {st.session_state.phase}."

    if aufruf.name == "setze_szenarien":
        typ = (aufruf.input.get("typ") or "").strip()
        baureihe = (aufruf.input.get("baureihe") or "").strip()
        optionen = aufruf.input.get("optionen") or []

        if typ not in SZENARIO_TYPEN:
            return (
                f"Unbekannter Szenario-Typ '{typ}'. Verfügbar sind: "
                f"{', '.join(SZENARIO_TYPEN)}."
            )
        if "Verlagerung" in typ and not baureihe:
            return "Für die Produktionsverlagerung muss eine Baureihe angegeben werden."

        gueltige = list(dict.fromkeys(o for o in optionen if o in VERFUEGBARE_OPTIONEN))
        if len(gueltige) < 2:
            return (
                "Es werden mindestens zwei gültige Optionen benötigt. "
                f"Verfügbar sind: {', '.join(VERFUEGBARE_OPTIONEN)}."
            )

        st.session_state.typ = typ
        st.session_state.baureihe = baureihe
        st.session_state.optionen = gueltige
        st.session_state.gewichte = initiale_gewichte()
        setze_slider_aus_gewichten(st.session_state.gewichte)
        st.session_state.nutzer_werte = {}
        st.session_state.basis_ergebnis = None
        st.session_state.sensitivitaet_ergebnis = None
        st.session_state.robustheit = None
        st.session_state.phase3_gestartet = False
        st.session_state.phase6_gestartet = False
        st.session_state.phase = 2
        return (
            f"Szenario gespeichert: {typ}; Baureihe: {baureihe}; "
            f"Optionen: {', '.join(gueltige)}. Phase 2 ist aktiv."
        )

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
                        gespeichert.append(f"{opt}: {k}")
                else:
                    try:
                        ziel[k] = float(v)
                        gespeichert.append(f"{opt}: {k}")
                    except (TypeError, ValueError):
                        continue

        offen = offene_werte()
        if offen:
            return (
                "Gespeichert: "
                + ("; ".join(gespeichert) if gespeichert else "kein gültiger Wert")
                + ". Noch fehlend: "
                + "; ".join(f"{o}: {', '.join(ks)}" for o, ks in offen.items())
                + ". Fragen Sie als Nächstes genau einen dieser Werte ab."
            )
        return (
            "Alle Werte wurden gespeichert. Fragen Sie nun in einem Satz, ob "
            "die vollständig ausgefüllte Tabelle korrekt ist und mit der "
            "Berechnung fortgefahren werden kann."
        )

    if aufruf.name == "speichere_robustheit":
        bewertung = (aufruf.input.get("bewertung") or "").strip()
        begruendung = (aufruf.input.get("begruendung") or "").strip()
        st.session_state.robustheit = {
            "bewertung": bewertung,
            "begruendung": begruendung,
        }
        st.session_state.phase = 6
        # Die nächste Modellantwort derselben Dialogrunde ist bereits die
        # Abschlusszusammenfassung. Ein zweiter Auto-Aufruf wird verhindert.
        st.session_state.phase6_gestartet = True
        return "Die Robustheitsbewertung wurde gespeichert. Phase 6 ist aktiv."

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
            st.error(
                "Die Verbindung zum Sprachmodell ist fehlgeschlagen. Bitte "
                "laden Sie die Seite neu und versuchen Sie es erneut. "
                f"Technischer Fehlertyp: {type(e).__name__}."
            )
            return

        st.session_state.messages.append(
            {"role": "assistant", "content": antwort.content}
        )
        tool_aufrufe = [
            b for b in antwort.content if getattr(b, "type", None) == "tool_use"
        ]
        if not tool_aufrufe:
            return

        ergebnisse = []
        for aufruf in tool_aufrufe:
            text = fuehre_werkzeug_aus(aufruf)
            ergebnisse.append(
                {
                    "type": "tool_result",
                    "tool_use_id": aufruf.id,
                    "content": text,
                }
            )
        st.session_state.messages.append(
            {"role": "user", "content": ergebnisse}
        )


def chat_eingabe(platzhalter="Ihre Antwort"):
    eingabe = st.chat_input(platzhalter)
    if eingabe:
        st.session_state.messages.append({"role": "user", "content": eingabe})
        with st.chat_message("user"):
            st.markdown(eingabe)
        with st.spinner("Antwort wird erstellt"):
            fuehre_dialog_runde()
        st.rerun()


# =============================================================
# SITZUNGSSPEICHER
# =============================================================
for key, default in [
    ("phase", 0),
    ("messages", []),
    ("typ", None),
    ("baureihe", ""),
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
# KOPF UND NAVIGATION
# =============================================================
st.title("Konfiguration globaler Produktionsnetzwerke")

with st.sidebar:
    st.subheader("Phasen")
    st.markdown("Bereits erreichte Phasen können erneut geöffnet werden.")
    for i in range(ANZAHL_PHASEN):
        ist_aktuell = i == st.session_state.phase
        erreichbar = i <= st.session_state.phase or (
            i <= 2 and st.session_state.typ is not None
        )
        status = "Aktuell" if ist_aktuell else (
            "Abgeschlossen" if i < st.session_state.phase else "Offen"
        )
        if st.button(
            f"{status} | {PHASEN[i]['titel']}",
            key=f"nav_{i}",
            disabled=not erreichbar or ist_aktuell,
            width="stretch",
        ):
            st.session_state.phase = i
            st.rerun()

    st.divider()
    if st.button("Neue Analyse starten", width="stretch"):
        for k in list(st.session_state.keys()):
            st.session_state.pop(k, None)
        st.rerun()

PHASE = st.session_state.phase
if st.session_state.typ:
    kontextzeile = (
        f"**Szenario-Typ:** {st.session_state.typ}  "
        f"  **Baureihe:** {st.session_state.baureihe or 'nicht angegeben'}  "
        f"  **Optionen:** {', '.join(st.session_state.optionen)}"
    )
    st.markdown(kontextzeile)


# =============================================================
# AUTO-START-TRIGGER
# =============================================================
if PHASE == 0 and not st.session_state.phase0_gestartet:
    st.session_state.phase0_gestartet = True
    with st.spinner("Anwendung wird gestartet"):
        st.session_state.messages.append(
            {
                "role": "user",
                "content": (
                    AUTO_MARKER
                    + " Starten Sie Phase 0 und erläutern Sie das Vorgehen."
                ),
            }
        )
        fuehre_dialog_runde()
    st.rerun()

if PHASE == 3 and not st.session_state.phase3_gestartet:
    st.session_state.phase3_gestartet = True
    with st.spinner("Datenlage wird geprüft"):
        st.session_state.messages.append(
            {
                "role": "user",
                "content": (
                    AUTO_MARKER
                    + " Starten Sie die Datenabfrage. Fragen Sie ausschließlich "
                    "den ersten noch fehlenden Wert in einem Satz ab."
                ),
            }
        )
        fuehre_dialog_runde()
    st.rerun()

if PHASE == 6 and not st.session_state.phase6_gestartet:
    if st.session_state.basis_ergebnis is None:
        st.warning(
            "Es liegt noch kein Basis-Ergebnis vor. Bitte führen Sie zunächst "
            "die Berechnung durch."
        )
        st.stop()
    st.session_state.phase6_gestartet = True
    with st.spinner("Zusammenfassung wird erstellt"):
        st.session_state.messages.append(
            {
                "role": "user",
                "content": (
                    AUTO_MARKER
                    + " Erstellen Sie die professionelle Abschlusszusammenfassung."
                ),
            }
        )
        fuehre_dialog_runde()
    st.rerun()


# =============================================================
# CHATVERLAUF
# =============================================================
# In Phase 3 wird die aktuelle Rückfrage bewusst unterhalb der Datentabelle
# dargestellt. In Phase 6 erscheint die aktuelle Abschlusszusammenfassung nur
# im vorgesehenen Zusammenfassungsabschnitt.
zeige_verlauf(letzte_assistentenantwort_auslassen=PHASE in (3, 6))


# =============================================================
# OBERFLAECHE DER AKTUELLEN PHASE
# =============================================================
if PHASE == 0:
    st.divider()
    st.markdown("**Überblick über den Entscheidungsprozess**")
    st.dataframe(
        [
            {"Phase": PHASEN[i]["titel"], "Inhalt": PHASEN[i]["kurz"]}
            for i in range(1, ANZAHL_PHASEN)
        ],
        width="stretch",
        hide_index=True,
    )

if PHASE == 2:
    st.divider()
    st.subheader(PHASEN[2]["titel"])
    st.markdown(
        "Legen Sie fest, welche Bedeutung die fünf Leistungsdimensionen für "
        "die vorliegende Entscheidung haben. Alle Dimensionen starten mit "
        "einer Gewichtung von 20 Prozent. Die Summe bleibt automatisch bei "
        "100 Prozent; bei einer Änderung werden die übrigen Regler angepasst."
    )
    zeige_gewichts_slider(ALLE_DIMENSIONEN)
    st.markdown(
        "Wenn Sie mit der Gewichtung einverstanden sind, teilen Sie mir im "
        "Chat mit, dass mit der Datenabfrage fortgefahren werden kann."
    )

if PHASE == 3:
    st.divider()
    st.subheader(PHASEN[3]["titel"])

    with st.chat_message("assistant"):
        st.markdown(
            "In dieser Phase werden die für das ausgewählte Szenario relevanten "
            "Daten zusammengeführt. Ein Teil der Werte liegt bereits in den "
            "Systemdaten vor. Die noch fehlenden Angaben frage ich anschließend "
            "einzeln bei Ihnen ab. Die folgende Tabelle zeigt den aktuellen "
            "Datenstand."
        )

    st.dataframe(datenuebersicht(), width="stretch", hide_index=True)

    with st.expander("Berechnungsgrundlagen der ergänzten Kennzahlen"):
        st.dataframe(
            formel_beispiele_fuer_ui(),
            width="stretch",
            hide_index=True,
        )
        st.markdown(
            "Die Werte aus dem Validierungsleitfaden sind nicht im Quellcode "
            "hinterlegt. Die Berechnung der abgeleiteten Kennzahlen erfolgt "
            "deterministisch im Anwendungscode."
        )

    zeige_aktuellen_bot_text()

if PHASE == 4:
    st.divider()
    st.subheader(PHASEN[4]["titel"])
    offen = offene_werte()
    if offen:
        st.warning(
            "Es fehlen noch Werte aus der Datenabfrage: "
            + "; ".join(f"{o}: {', '.join(ks)}" for o, ks in offen.items())
        )
        st.stop()

    if st.session_state.basis_ergebnis is None:
        st.session_state.basis_ergebnis = rechne()
    erg = st.session_state.basis_ergebnis

    st.markdown(
        "**Normierung und Wirkungsrichtung:** Für Kennzahlen, bei denen der "
        "Zielwert oberhalb des Grenzwerts liegt, führen höhere Istwerte zu "
        "einer besseren Bewertung. Liegt der Zielwert unterhalb des "
        "Grenzwerts, führen niedrigere Istwerte zu einer besseren Bewertung. "
        "Für beide Wirkungsrichtungen wird jeweils die zugehörige "
        "ziel- und grenzwertbasierte Berechnung angewendet. Werte außerhalb "
        "des Ziel-Grenz-Bereichs werden auf 0 beziehungsweise 100 begrenzt."
    )

    st.markdown("**Normwerte der Kennzahlen**")
    aktiv = aktive_kennzahlen(MATRIX, st.session_state.typ)
    zeilen = []
    for k in aktiv:
        zeile = {"Leistungsdimension": KPIS[k]["dimension"], "Kennzahl": k}
        for opt in st.session_state.optionen:
            zeile[opt] = erg["normwerte"].get(opt, {}).get(k, "Nicht verfügbar")
        zeilen.append(zeile)
    st.dataframe(zeilen, width="stretch", hide_index=True)

    st.markdown("**Werte der Leistungsdimensionen**")
    zeilen = []
    for d in ALLE_DIMENSIONEN:
        zeile = {
            "Leistungsdimension": d,
            "Gewichtung": f"{erg['gewichte'].get(d, 0) * 100:.0f} %",
        }
        for opt in st.session_state.optionen:
            zeile[opt] = erg["dim_scores"].get(opt, {}).get(d, "Nicht verfügbar")
        zeilen.append(zeile)
    st.dataframe(zeilen, width="stretch", hide_index=True)

    st.markdown("**Gesamtnutzwerte**")
    st.dataframe(
        [
            {
                "Rang": erg["raenge"][o],
                "Option": o,
                "Nutzwert": erg["nutzwerte"][o],
            }
            for o in sorted(
                erg["nutzwerte"],
                key=erg["nutzwerte"].get,
                reverse=True,
            )
        ],
        width="stretch",
        hide_index=True,
    )
    st.info(
        f"Empfehlung auf Grundlage der initialen Gewichtung: {erg['empfehlung']}"
    )
    st.markdown(
        "Wenn Sie mit der dargestellten Berechnung fortfahren möchten, teilen "
        "Sie mir im Chat mit, dass die Sensitivitätsanalyse begonnen werden kann."
    )

if PHASE == 5:
    st.divider()
    st.subheader(PHASEN[5]["titel"])
    if st.session_state.basis_ergebnis is None:
        st.warning(
            "Es liegt noch kein Basis-Ergebnis vor. Bitte führen Sie zunächst "
            "die Berechnung durch."
        )
        st.stop()

    st.markdown(
        "Verändern Sie die Gewichtungen und berechnen Sie das Ergebnis erneut. "
        "Auf diese Weise prüfen Sie, ob die Empfehlung bei unterschiedlichen "
        "Prioritäten stabil bleibt. Die ursprüngliche Gewichtung bleibt für "
        "die Abschlussdokumentation unverändert gespeichert."
    )

    if "sensitivitaet_gewichte" not in st.session_state:
        st.session_state.sensitivitaet_gewichte = dict(
            st.session_state.basis_ergebnis["gewichte"]
        )
        setze_slider_aus_gewichten(st.session_state.sensitivitaet_gewichte)

    st.session_state.gewichte = st.session_state.sensitivitaet_gewichte
    zeige_gewichts_slider(
        ALLE_DIMENSIONEN,
        ziel_key="sensitivitaet_gewichte",
    )

    if st.button("Ergebnis neu berechnen"):
        st.session_state.sensitivitaet_ergebnis = rechne_mit_gewichten(
            st.session_state.sensitivitaet_gewichte
        )
        st.rerun()

    erg = st.session_state.sensitivitaet_ergebnis or st.session_state.basis_ergebnis
    st.dataframe(
        [
            {
                "Rang": erg["raenge"][o],
                "Option": o,
                "Nutzwert": erg["nutzwerte"][o],
            }
            for o in sorted(
                erg["nutzwerte"],
                key=erg["nutzwerte"].get,
                reverse=True,
            )
        ],
        width="stretch",
        hide_index=True,
    )
    st.info(f"Aktuelle Empfehlung im Sensitivitätstest: {erg['empfehlung']}")
    st.markdown(
        "Nachdem Sie mehrere Gewichtungen geprüft haben, teilen Sie mir im "
        "Chat mit, ob Sie das Ergebnis als robust oder nicht robust bewerten. "
        "Diese Einschätzung wird in der Zusammenfassung dokumentiert."
    )

if PHASE == 6 and st.session_state.basis_ergebnis:
    st.divider()
    st.subheader(PHASEN[6]["titel"])
    erg = st.session_state.basis_ergebnis

    st.markdown("**Gewichtungen der Leistungsdimensionen**")
    st.dataframe(
        [
            {
                "Leistungsdimension": d,
                "Gewichtung": f"{g * 100:.0f} %",
            }
            for d, g in erg["gewichte"].items()
        ],
        width="stretch",
        hide_index=True,
    )

    st.markdown("**Finale Werte der Leistungsdimensionen**")
    zeilen = []
    for d in erg["gewichte"]:
        zeile = {"Leistungsdimension": d}
        for opt in st.session_state.optionen:
            zeile[opt] = erg["dim_scores"].get(opt, {}).get(d, "Nicht verfügbar")
        zeilen.append(zeile)
    st.dataframe(zeilen, width="stretch", hide_index=True)

    st.markdown("**Textliche Zusammenfassung des Vorgehens und der Ergebnisse**")
    zeige_aktuellen_bot_text()

    pdf_bytes = erstelle_ergebnis_pdf(
        erg,
        letzter_bot_text(),
        st.session_state.typ or "",
        st.session_state.baureihe or "",
        st.session_state.optionen,
        KPIS,
        aktive_kennzahlen(MATRIX, st.session_state.typ)
        if st.session_state.typ
        else [],
        st.session_state.robustheit,
    )
    st.download_button(
        "Ergebnis-PDF herunterladen",
        data=pdf_bytes,
        file_name="entscheidungsempfehlung_produktionsnetzwerk.pdf",
        mime="application/pdf",
    )


# =============================================================
# EINGABEZEILE
# =============================================================
chat_eingabe()
