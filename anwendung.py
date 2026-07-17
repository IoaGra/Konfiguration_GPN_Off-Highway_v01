"""Streamlit-Anwendung zur Konfiguration globaler Produktionsnetzwerke.

Das Sprachmodell führt den Dialog. Sämtliche numerischen Berechnungen werden
in den Python-Modulen der Anwendung deterministisch ausgeführt.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from html import escape
from typing import Optional

import anthropic
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from bewertungslogik import berechne_nutzwerte
from datengrundlage import dimensionen_aus_kpis, lade_daten
from ergebnis_pdf import erstelle_ergebnis_pdf
from kennzahlenberechnung import (
    berechne_formel_kennzahl,
    faktor_information,
    faktoren_fuer,
    ist_formel_kennzahl,
    naechster_fehlender_faktor,
)
from leistungsdimensionen import DIMENSION_BESCHREIBUNGEN
from prozessphasen import ANZAHL_PHASEN, PHASEN
from szenarien import SZENARIO_BESCHREIBUNGEN
from szenario_kennzahl_matrix import (
    aktive_kennzahlen,
    lade_matrix,
    vereinigte_kennzahlen,
)

st.set_page_config(
    page_title="Konfiguration globaler Produktionsnetzwerke",
    layout="wide",
)

MODELL = st.secrets.get("CLAUDE_MODEL", "claude-sonnet-5")
MAX_TOKENS = 1200
AUTO_MARKER = "[AUTO]"
ZUSAETZLICHE_DATENOPTIONEN = ["Standort C"]

STANDARD_GEWICHTE = {
    "Effizienz": 0.20,
    "Qualität": 0.20,
    "Zeit": 0.20,
    "Flexibilität": 0.20,
    "Ökologische Nachhaltigkeit": 0.20,
}

HERKUNFT_LABEL = {
    "system": "Systemwert",
    "nutzer_direkt": "Direkte Eingabe",
    "nutzer_berechnet": "Im Code berechnet",
    "nutzer": "Nutzereingabe",
}

st.markdown(
    """
    <style>
    :root {
        --app-bg: #212121;
        --sidebar-bg: #171717;
        --surface: #2f2f2f;
        --surface-hover: #383838;
        --text: #ffffff;
        --muted: #c5c5c5;
        --accent: #2f81f7;
        --border: #474747;
        --danger: #ff6b6b;
        --done: #1f3a2a;
        --done-border: #477a59;
    }

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background: var(--app-bg) !important;
        color: var(--text) !important;
        overflow-anchor: none !important;
        scroll-behavior: auto !important;
    }

    [data-testid="stHeader"] {
        background: rgba(33, 33, 33, 0.94) !important;
    }

    [data-testid="stSidebar"] {
        background: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border) !important;
    }

    .block-container {
        max-width: 1060px !important;
        padding-top: 1.8rem !important;
        padding-bottom: 7rem !important;
    }

    .stApp p, .stApp span, .stApp label, .stApp li,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4,
    .stMarkdown, [data-testid="stText"],
    [data-testid="stCaptionContainer"] {
        color: var(--text) !important;
    }

    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: 0 !important;
        padding: 0.65rem 0 !important;
        margin: 0 0 0.35rem 0 !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: var(--surface) !important;
        border-radius: 18px !important;
        margin-left: 18% !important;
        padding: 0.75rem 1rem !important;
    }

    [data-testid="stChatMessageAvatarAssistant"],
    [data-testid="stChatMessageAvatarUser"] {
        background: transparent !important;
    }

    .stButton > button, .stDownloadButton > button {
        background: var(--surface) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }

    .stButton > button:hover, .stDownloadButton > button:hover {
        background: var(--surface-hover) !important;
        border-color: var(--accent) !important;
        color: var(--text) !important;
    }

    .phase-card {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.7rem 0.55rem;
        margin-bottom: 0.55rem;
        text-align: center;
        background: #232323;
    }

    .phase-card.done {
        background: var(--done);
        border-color: var(--done-border);
    }

    .phase-card.current {
        border-color: var(--accent);
        box-shadow: inset 0 0 0 1px var(--accent);
    }

    .phase-title {
        font-size: 0.88rem;
        font-weight: 650;
        line-height: 1.25;
        color: #ffffff;
    }

    .phase-status {
        font-size: 0.76rem;
        margin-top: 0.38rem;
        color: #ffffff;
        text-align: center;
    }

    [data-testid="stBottom"],
    [data-testid="stBottom"] > div,
    [data-testid="stBottomBlockContainer"] {
        background: var(--app-bg) !important;
    }

    [data-testid="stBottomBlockContainer"] {
        max-width: 1060px !important;
        margin: 0 auto !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    [data-testid="stChatInput"] {
        background: transparent !important;
        border: 0 !important;
        border-radius: 24px !important;
        box-shadow: none !important;
        overflow: visible !important;
        margin: 0 !important;
    }

    [data-testid="stChatInput"] > div {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 24px !important;
        box-shadow: none !important;
        overflow: hidden !important;
        min-height: 52px !important;
    }

    [data-testid="stChatInput"] > div:focus-within {
        border-color: var(--accent) !important;
    }

    [data-testid="stChatInput"] [data-baseweb="textarea"],
    [data-testid="stChatInput"] [data-baseweb="textarea"] > div,
    [data-testid="stChatInput"] textarea {
        background: var(--surface) !important;
        background-color: var(--surface) !important;
        border: 0 !important;
        box-shadow: none !important;
        color: var(--text) !important;
        caret-color: var(--text) !important;
        margin: 0 !important;
        text-indent: 0 !important;
        line-height: 1.45 !important;
    }

    [data-testid="stChatInput"] textarea {
        padding: 0.9rem 3.7rem 0.9rem 1.15rem !important;
        min-height: 50px !important;
        overflow-y: auto !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #d6d6d6 !important;
        opacity: 0.78 !important;
    }

    [data-testid="stChatInput"] button {
        background: transparent !important;
        border: 0 !important;
        color: var(--text) !important;
        margin-right: 0.35rem !important;
    }

    .app-table-wrapper {
        display: flex;
        justify-content: center;
        width: 100%;
        margin: 0.8rem auto 1.15rem auto;
    }

    .app-table-shell {
        max-width: 100%;
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: visible;
        background: var(--surface);
    }

    table.app-table {
        width: 100%;
        max-width: 100%;
        border-collapse: collapse;
        table-layout: auto;
        margin: 0 auto;
        color: var(--text);
        background: var(--surface);
        font-size: clamp(0.70rem, 0.86vw, 0.90rem);
    }

    table.app-table th {
        background: #17365d;
        color: #ffffff !important;
        font-weight: 650;
        text-align: left;
        padding: 0.62rem 0.68rem;
        border-right: 1px solid #31557f;
        border-bottom: 1px solid #31557f;
        white-space: normal;
        overflow-wrap: normal;
        word-break: normal;
        hyphens: none;
    }

    table.app-table td {
        background: var(--surface);
        color: #ffffff !important;
        padding: 0.56rem 0.68rem;
        border-right: 1px solid var(--border);
        border-bottom: 1px solid var(--border);
        vertical-align: top;
        white-space: normal;
        overflow-wrap: normal;
        word-break: normal;
        hyphens: none;
    }

    table.app-table th:last-child, table.app-table td:last-child {
        border-right: 0;
    }

    table.app-table tr:last-child td {
        border-bottom: 0;
    }

    table.app-table .narrow-column {
        min-width: 5.5rem;
        white-space: nowrap !important;
        text-align: center;
    }

    table.app-table .numeric-cell {
        text-align: right;
        white-space: nowrap;
    }

    table.app-table .missing-cell {
        color: var(--danger) !important;
        font-weight: 700;
    }

    table.app-table .not-relevant-cell {
        color: #b8b8b8 !important;
        font-style: italic;
    }

    [data-testid="stAlert"] {
        color: var(--text) !important;
    }

    [data-baseweb="slider"] div[role="slider"] {
        background-color: var(--accent) !important;
    }

    hr {
        border-color: var(--border) !important;
    }

    a {
        color: #75adff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def bewahre_scrollposition():
    """Stellt nach einem Rerun die selbst gewählte Scrollposition wieder her."""
    components.html(
        """
        <script>
        (() => {
            let w, d;
            try { w = window.parent; d = w.document; } catch (e) { return; }
            const positionKey = "gpn_scroll_position";
            const restoreKey = "gpn_restore_scroll";
            const save = () => {
                try {
                    w.sessionStorage.setItem(positionKey, String(w.scrollY || 0));
                    w.sessionStorage.setItem(restoreKey, "1");
                } catch (e) {}
            };
            const install = () => {
                const textarea = d.querySelector('[data-testid="stChatInput"] textarea');
                const button = d.querySelector('[data-testid="stChatInput"] button');
                if (textarea && !textarea.dataset.gpnHandler) {
                    textarea.dataset.gpnHandler = "1";
                    textarea.addEventListener("keydown", (event) => {
                        if (event.key === "Enter" && !event.shiftKey) save();
                    }, true);
                }
                if (button && !button.dataset.gpnHandler) {
                    button.dataset.gpnHandler = "1";
                    button.addEventListener("click", save, true);
                }
            };
            const restore = () => {
                try {
                    if (w.sessionStorage.getItem(restoreKey) !== "1") return;
                    const y = Number(w.sessionStorage.getItem(positionKey) || "0");
                    [0, 100, 250, 500].forEach((delay) => {
                        w.setTimeout(() => w.scrollTo({top: y, left: 0, behavior: "auto"}), delay);
                    });
                    w.setTimeout(() => w.sessionStorage.removeItem(restoreKey), 700);
                } catch (e) {}
            };
            install();
            if (!w.__gpnScrollObserver) {
                w.__gpnScrollObserver = new MutationObserver(install);
                w.__gpnScrollObserver.observe(d.body, {childList: true, subtree: true});
            }
            restore();
        })();
        </script>
        """,
        height=0,
    )


try:
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
except Exception:
    st.error(
        "Kein API-Schlüssel gefunden. Hinterlegen Sie in den App-Einstellungen "
        "unter 'Secrets' den Eintrag ANTHROPIC_API_KEY."
    )
    st.stop()


@st.cache_data
def _lade_alles():
    kpis, optionen, werte, fehlend = lade_daten("datengrundlage.xlsx")
    typen, matrix = lade_matrix("szenario_kennzahl_matrix.xlsx")
    return kpis, optionen, werte, fehlend, typen, matrix


try:
    KPIS, EXCEL_OPTIONEN, SYSTEM_WERTE, FEHLEND, SZENARIO_TYPEN, MATRIX = _lade_alles()
except Exception as fehler:
    st.error(f"Die Datengrundlage konnte nicht geladen werden: {fehler}")
    st.stop()

ALLE_DIMENSIONEN = dimensionen_aus_kpis(KPIS)
VERFUEGBARE_DATENOPTIONEN = list(
    dict.fromkeys(EXCEL_OPTIONEN + ZUSAETZLICHE_DATENOPTIONEN)
)


def initiale_gewichte() -> dict[str, float]:
    basis = {dimension: STANDARD_GEWICHTE.get(dimension, 0.0) for dimension in ALLE_DIMENSIONEN}
    summe = sum(basis.values())
    if summe <= 0:
        return {dimension: 1.0 / len(ALLE_DIMENSIONEN) for dimension in ALLE_DIMENSIONEN}
    return {dimension: wert / summe for dimension, wert in basis.items()}


def alternative_namen() -> list[str]:
    return [str(alt.get("name", "")) for alt in st.session_state.alternativen]


def alternative_nach_name(name: str) -> Optional[dict]:
    for alternative in st.session_state.alternativen:
        if alternative.get("name") == name:
            return alternative
    return None


def aktive_kennzahlen_alternative(alternative: dict) -> list[str]:
    return aktive_kennzahlen(MATRIX, alternative.get("szenario_typ", ""))


def aktive_kennzahlen_nach_alternative() -> dict[str, list[str]]:
    return {
        alternative["name"]: aktive_kennzahlen_alternative(alternative)
        for alternative in st.session_state.alternativen
    }


def aktive_kennzahlen_gesamt() -> list[str]:
    typen = [alt.get("szenario_typ", "") for alt in st.session_state.alternativen]
    return vereinigte_kennzahlen(MATRIX, typen)


def baue_rohwerte():
    rohwerte: dict[str, dict] = {}
    herkunft: dict[str, dict] = {}
    for alternative in st.session_state.alternativen:
        name = alternative["name"]
        datenoption = alternative["datenoption"]
        aktiv = aktive_kennzahlen_alternative(alternative)
        rohwerte[name] = {}
        herkunft[name] = {}

        for kennzahl in aktiv:
            if kennzahl in SYSTEM_WERTE.get(datenoption, {}):
                rohwerte[name][kennzahl] = SYSTEM_WERTE[datenoption][kennzahl]
                herkunft[name][kennzahl] = "system"

        for kennzahl, wert in st.session_state.nutzer_werte.get(name, {}).items():
            if kennzahl in aktiv:
                rohwerte[name][kennzahl] = wert
                herkunft[name][kennzahl] = (
                    st.session_state.nutzer_quelle.get(name, {}).get(kennzahl, "nutzer")
                )
    return rohwerte, herkunft


def offene_werte() -> dict[str, list[str]]:
    rohwerte, _ = baue_rohwerte()
    offen: dict[str, list[str]] = {}
    for alternative in st.session_state.alternativen:
        name = alternative["name"]
        fehlt = [
            kennzahl
            for kennzahl in aktive_kennzahlen_alternative(alternative)
            if kennzahl not in rohwerte.get(name, {})
        ]
        if fehlt:
            offen[name] = fehlt
    return offen


def rechne_mit_gewichten(gewichte: dict[str, float]) -> dict:
    rohwerte, herkunft = baue_rohwerte()
    ergebnis = berechne_nutzwerte(
        rohwerte,
        aktive_kennzahlen_nach_alternative(),
        KPIS,
        gewichte,
    )
    ergebnis["rohwerte"] = rohwerte
    ergebnis["herkunft"] = herkunft
    ergebnis["eingabefaktoren"] = deepcopy(st.session_state.phase3_faktoren)
    ergebnis["eingabemodi"] = deepcopy(st.session_state.phase3_modus)
    ergebnis["alternativen"] = deepcopy(st.session_state.alternativen)
    return ergebnis


def rechne() -> dict:
    return rechne_mit_gewichten(st.session_state.gewichte)


def slider_geaendert(
    geaendert: str,
    dimensionen: list[str],
    ziel_key: str,
    prefix: str,
):
    neu = st.session_state[f"{prefix}_{geaendert}"]
    andere = [dimension for dimension in dimensionen if dimension != geaendert]
    if not andere:
        return
    rest_alt = sum(st.session_state[f"{prefix}_{dimension}"] for dimension in andere)
    rest_neu = 100 - neu
    if rest_alt <= 0:
        for dimension in andere:
            st.session_state[f"{prefix}_{dimension}"] = rest_neu / len(andere)
    else:
        faktor = rest_neu / rest_alt
        verteilt = 0
        for dimension in andere[:-1]:
            wert = round(st.session_state[f"{prefix}_{dimension}"] * faktor)
            st.session_state[f"{prefix}_{dimension}"] = wert
            verteilt += wert
        st.session_state[f"{prefix}_{andere[-1]}"] = rest_neu - verteilt
    for dimension in dimensionen:
        st.session_state[ziel_key][dimension] = (
            st.session_state[f"{prefix}_{dimension}"] / 100.0
        )


def setze_slider_aus_gewichten(gewichte: dict, prefix: str):
    for dimension in ALLE_DIMENSIONEN:
        st.session_state[f"{prefix}_{dimension}"] = round(
            gewichte.get(dimension, 0.0) * 100
        )


def zeige_gewichts_slider(dimensionen: list[str], ziel_key: str, prefix: str):
    for dimension in dimensionen:
        schluessel = f"{prefix}_{dimension}"
        if schluessel not in st.session_state:
            st.session_state[schluessel] = round(
                st.session_state[ziel_key].get(dimension, 0.0) * 100
            )
    for dimension in dimensionen:
        st.slider(
            dimension,
            min_value=0,
            max_value=100,
            key=f"{prefix}_{dimension}",
            on_change=slider_geaendert,
            args=(dimension, dimensionen, ziel_key, prefix),
        )
    summe = sum(st.session_state[f"{prefix}_{dimension}"] for dimension in dimensionen)
    st.markdown(f"**Summe der Gewichtungen: {summe} %**")


def _block_attr(block, name):
    return block.get(name) if isinstance(block, dict) else getattr(block, name, None)


def _assistant_hat_tool_use(nachricht: dict) -> bool:
    return (
        nachricht.get("role") == "assistant"
        and isinstance(nachricht.get("content"), list)
        and any(
            _block_attr(block, "type") == "tool_use"
            for block in nachricht["content"]
        )
    )


def _index_letzte_assistentennachricht() -> Optional[int]:
    for index in range(len(st.session_state.messages) - 1, -1, -1):
        nachricht = st.session_state.messages[index]
        if nachricht["role"] == "assistant" and isinstance(nachricht["content"], list):
            if any(_block_attr(block, "type") == "text" for block in nachricht["content"]):
                return index
    return None


def zeige_verlauf(letzte_assistentenantwort_auslassen: bool = False):
    auslassen = (
        _index_letzte_assistentennachricht()
        if letzte_assistentenantwort_auslassen
        else None
    )
    for index, nachricht in enumerate(st.session_state.messages):
        if index == auslassen:
            continue
        if nachricht["role"] == "user":
            inhalt = nachricht["content"]
            if isinstance(inhalt, str) and not inhalt.startswith(AUTO_MARKER):
                with st.chat_message("user"):
                    st.markdown(inhalt)
        elif nachricht["role"] == "assistant" and isinstance(nachricht["content"], list):
            # Text, der zusammen mit einem Werkzeugaufruf erzeugt wurde, bleibt
            # unsichtbar. Dadurch erscheint pro Nutzereingabe nur eine Antwort.
            if _assistant_hat_tool_use(nachricht):
                continue
            for block in nachricht["content"]:
                if _block_attr(block, "type") == "text":
                    text = _block_attr(block, "text")
                    if text:
                        with st.chat_message("assistant"):
                            st.markdown(text)


def letzter_bot_text() -> str:
    for nachricht in reversed(st.session_state.messages):
        if nachricht["role"] == "assistant" and isinstance(nachricht["content"], list):
            if _assistant_hat_tool_use(nachricht):
                continue
            texte = [
                _block_attr(block, "text")
                for block in nachricht["content"]
                if _block_attr(block, "type") == "text" and _block_attr(block, "text")
            ]
            if texte:
                return "\n".join(texte)
    return ""


def zeige_aktuellen_bot_text():
    text = letzter_bot_text()
    if text:
        with st.chat_message("assistant"):
            st.markdown(text)


def _assistententext_hinzufuegen(text: str):
    st.session_state.messages.append(
        {"role": "assistant", "content": [{"type": "text", "text": text}]}
    )


def _tabellenzeilen(daten):
    if daten is None:
        return [], []
    if hasattr(daten, "data") and isinstance(getattr(daten, "data"), pd.DataFrame):
        daten = daten.data
    if isinstance(daten, pd.DataFrame):
        if daten.empty:
            return [], []
        return [str(spalte) for spalte in daten.columns], daten.to_dict(orient="records")
    if isinstance(daten, dict):
        daten = [daten]
    daten = list(daten)
    if not daten:
        return [], []
    if isinstance(daten[0], dict):
        spalten = list(daten[0].keys())
        for zeile in daten[1:]:
            for spalte in zeile:
                if spalte not in spalten:
                    spalten.append(spalte)
        return [str(spalte) for spalte in spalten], daten
    spalten = [str(index + 1) for index in range(len(daten[0]))]
    return spalten, [dict(zip(spalten, zeile)) for zeile in daten]


def _tabellenwert(wert) -> str:
    if wert is None:
        return "—"
    if isinstance(wert, float):
        return f"{wert:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return str(wert)


def _spaltenbreiten(spalten: list[str], zeilen: list[dict]) -> list[float]:
    gewichte = []
    for spalte in spalten:
        laengen = [len(spalte)]
        for zeile in zeilen:
            laengen.append(len(_tabellenwert(zeile.get(spalte, ""))))
        maximale_laenge = max(laengen)
        if spalte in {"Nr.", "Rang"}:
            gewicht = max(9, len(spalte) + 4)
        else:
            gewicht = max(len(spalte) + 2, min(maximale_laenge + 1, 34))
        gewichte.append(float(gewicht))
    summe = sum(gewichte) or 1.0
    return [gewicht / summe * 100 for gewicht in gewichte]


def zeige_tabelle_zentriert(daten):
    spalten, zeilen = _tabellenzeilen(daten)
    if not spalten:
        st.markdown("Keine Daten verfügbar.")
        return
    breiten = _spaltenbreiten(spalten, zeilen)
    colgroup = "".join(
        f'<col style="width:{breite:.2f}%">' for breite in breiten
    )
    kopf = []
    for spalte in spalten:
        klasse = "narrow-column" if spalte in {"Nr.", "Rang"} else ""
        kopf.append(f'<th class="{klasse}">{escape(spalte)}</th>')
    koerper = []
    for zeile in zeilen:
        zellen = []
        for spalte in spalten:
            rohwert = zeile.get(spalte, "")
            text = _tabellenwert(rohwert)
            klassen = []
            if spalte in {"Nr.", "Rang"}:
                klassen.append("narrow-column")
            if isinstance(rohwert, (int, float)) and not isinstance(rohwert, bool):
                klassen.append("numeric-cell")
            if text.strip() == "Fehlender Wert":
                klassen.append("missing-cell")
            if text.strip() == "Nicht relevant":
                klassen.append("not-relevant-cell")
            zellen.append(
                f'<td class="{" ".join(klassen)}">'
                f'{escape(text).replace(chr(10), "<br>")}</td>'
            )
        koerper.append("<tr>" + "".join(zellen) + "</tr>")
    html = (
        '<div class="app-table-wrapper"><div class="app-table-shell">'
        '<table class="app-table"><colgroup>'
        + colgroup
        + '</colgroup><thead><tr>'
        + "".join(kopf)
        + '</tr></thead><tbody>'
        + "".join(koerper)
        + '</tbody></table></div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def datenuebersicht() -> list[dict]:
    rohwerte, herkunft = baue_rohwerte()
    zeilen = []
    for kennzahl in aktive_kennzahlen_gesamt():
        zeile = {
            "Leistungsdimension": KPIS[kennzahl]["dimension"],
            "Kennzahl": kennzahl,
            "Einheit": KPIS[kennzahl]["einheit"],
        }
        for alternative in st.session_state.alternativen:
            name = alternative["name"]
            if kennzahl not in aktive_kennzahlen_alternative(alternative):
                zeile[name] = "Nicht relevant"
            elif kennzahl in rohwerte.get(name, {}):
                quelle = HERKUNFT_LABEL.get(
                    herkunft.get(name, {}).get(kennzahl, ""),
                    "Nutzereingabe",
                )
                zeile[name] = f"{_tabellenwert(rohwerte[name][kennzahl])} ({quelle})"
            else:
                zeile[name] = "Fehlender Wert"
        zeilen.append(zeile)
    return zeilen


def _zahl_token_lesen(token: str) -> Optional[float]:
    token = str(token or "").strip().replace(" ", "")
    if not token:
        return None
    try:
        if "," in token:
            token = token.replace(".", "").replace(",", ".")
        elif token.count(".") > 1:
            token = token.replace(".", "")
        elif token.count(".") == 1:
            links, rechts = token.split(".")
            if len(rechts) == 3 and links:
                token = links + rechts
        return float(token)
    except (TypeError, ValueError):
        return None


def _deutsche_zahlen_lesen(text: str) -> list[float]:
    treffer = re.findall(r"[-+]?\d[\d. ]*(?:,\d+)?", text or "")
    werte = []
    for treffer_text in treffer:
        wert = _zahl_token_lesen(treffer_text)
        if wert is not None:
            werte.append(wert)
    return werte


def _deutsche_zahl_lesen(text: str) -> Optional[float]:
    werte = _deutsche_zahlen_lesen(text)
    return werte[-1] if werte else None


def _alias_im_text(normierter_text: str, alias: str) -> bool:
    muster = r"(?<![a-z0-9])" + re.escape(_norm_text(alias)) + r"(?![a-z0-9])"
    return re.search(muster, normierter_text) is not None


def _wert_nahe_alias(text: str, aliases: tuple[str, ...]) -> Optional[float]:
    normiert = _norm_text(text)
    zahlenmuster = r"[-+]?\d[\d. ]*(?:,\d+)?"
    for alias in aliases:
        alias_norm = _norm_text(alias)
        muster = r"(?<![a-z0-9])" + re.escape(alias_norm) + r"(?![a-z0-9])"
        treffer = re.search(muster, normiert)
        if not treffer:
            continue
        danach = normiert[treffer.end():treffer.end() + 90]
        zahl_danach = re.search(zahlenmuster, danach)
        if zahl_danach:
            return _zahl_token_lesen(zahl_danach.group(0))
        davor = normiert[max(0, treffer.start() - 55):treffer.start()]
        zahlen_davor = re.findall(zahlenmuster, davor)
        if zahlen_davor:
            return _zahl_token_lesen(zahlen_davor[-1])
    return None


def _wert_ist_plausibel(kennzahl: str, wert: Optional[float]) -> bool:
    if wert is None:
        return False
    if kennzahl in {"Qualitätsrate", "Anteil erneuerbarer Energien"}:
        return 0 <= wert <= 100
    return wert > 0


def _modus(alt_name: str, kennzahl: str) -> Optional[str]:
    return st.session_state.phase3_modus.get(alt_name, {}).get(kennzahl)


def _setze_modus(alt_name: str, kennzahl: str, modus: str):
    st.session_state.phase3_modus.setdefault(alt_name, {})[kennzahl] = modus


def _faktoren(alt_name: str, kennzahl: str) -> dict:
    return (
        st.session_state.phase3_faktoren
        .setdefault(alt_name, {})
        .setdefault(kennzahl, {})
    )


def _speichere_direktwert(alt_name: str, kennzahl: str, wert: float):
    st.session_state.nutzer_werte.setdefault(alt_name, {})[kennzahl] = float(wert)
    st.session_state.nutzer_quelle.setdefault(alt_name, {})[kennzahl] = "nutzer_direkt"
    _setze_modus(alt_name, kennzahl, "direkt")


def _aktualisiere_berechneten_wert(alt_name: str, kennzahl: str) -> bool:
    alternative = alternative_nach_name(alt_name)
    if not alternative:
        return False
    ergebnis = berechne_formel_kennzahl(
        kennzahl,
        _faktoren(alt_name, kennzahl),
        alternative["datenoption"],
    )
    if ergebnis is None:
        st.session_state.nutzer_werte.setdefault(alt_name, {}).pop(kennzahl, None)
        st.session_state.nutzer_quelle.setdefault(alt_name, {}).pop(kennzahl, None)
        return False
    st.session_state.nutzer_werte.setdefault(alt_name, {})[kennzahl] = ergebnis
    st.session_state.nutzer_quelle.setdefault(alt_name, {})[kennzahl] = "nutzer_berechnet"
    return True


def _naechste_phase3_aktion():
    rohwerte, _ = baue_rohwerte()
    for alternative in st.session_state.alternativen:
        name = alternative["name"]
        datenoption = alternative["datenoption"]
        for kennzahl in aktive_kennzahlen_alternative(alternative):
            if kennzahl in rohwerte.get(name, {}):
                continue
            if ist_formel_kennzahl(kennzahl, datenoption):
                if _aktualisiere_berechneten_wert(name, kennzahl):
                    rohwerte, _ = baue_rohwerte()
                    continue
                faktor = naechster_fehlender_faktor(
                    kennzahl,
                    _faktoren(name, kennzahl),
                    datenoption,
                )
                return ("formel", name, kennzahl, faktor)
            return ("wert", name, kennzahl, None)
    return None


def _frage_fuer_aktion(aktion) -> str:
    art, alt_name, kennzahl, faktor = aktion
    alternative = alternative_nach_name(alt_name) or {}
    datenoption = alternative.get("datenoption", "")
    einheit = KPIS.get(kennzahl, {}).get("einheit", "")
    if art == "formel":
        vorhandene = _faktoren(alt_name, kennzahl)
        fehlende = [
            (schluessel, bezeichnung, faktor_einheit)
            for schluessel, bezeichnung, faktor_einheit
            in faktoren_fuer(kennzahl, datenoption)
            if schluessel not in vorhandene
        ]
        bezeichnungen = [bezeichnung for _, bezeichnung, _ in fehlende]
        if len(bezeichnungen) > 1:
            teilwert_text = ", ".join(bezeichnungen[:-1]) + " und " + bezeichnungen[-1]
            zusatz = " Sie können beide Werte in einer Nachricht angeben."
        else:
            teilwert_text = bezeichnungen[0] if bezeichnungen else "die noch fehlenden Teilwerte"
            zusatz = ""
        return (
            f"Für die Kennzahl {kennzahl} der Alternative {alt_name} benötige "
            f"ich {teilwert_text}.{zusatz} Falls Ihnen {kennzahl} bereits als "
            "fertiger Istwert vorliegt, können Sie diesen auch direkt angeben."
        )
    return (
        f"Welchen Istwert möchten Sie für {kennzahl} der Alternative "
        f"{alt_name} in {einheit} angeben?"
    )


def _ist_bestaetigung(text: str) -> bool:
    bereinigt = (text or "").strip().lower()
    schluessel = (
        "ja", "passt", "korrekt", "richtig", "weiter", "fortfahren",
        "kann weiter", "können weiter", "einverstanden", "stimmt",
    )
    return any(wort in bereinigt for wort in schluessel)


def _norm_text(text: str) -> str:
    return (
        (text or "").lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )


def _alternative_aus_text(text: str, aktuelle_aktion=None) -> Optional[str]:
    normiert = _norm_text(text)
    treffer = []
    for alternative in st.session_state.alternativen:
        name = alternative["name"]
        datenoption = alternative["datenoption"]
        if _norm_text(name) in normiert or _norm_text(datenoption) in normiert:
            treffer.append(name)
    if len(set(treffer)) == 1:
        return treffer[0]
    if aktuelle_aktion:
        return aktuelle_aktion[1]
    return None


def _versuche_benannte_aenderung(text: str, aktuelle_aktion=None) -> Optional[str]:
    """Speichert eine oder mehrere eindeutig benannte Angaben aus einer Nachricht."""
    normiert = _norm_text(text)
    alt_name = _alternative_aus_text(text, aktuelle_aktion)
    meldungen = []

    faktor_definitionen = [
        (("fertigungseinzelkosten", "fertigungseinzelkosten pro produktionseinheit"),
         "Fertigungskosten", "fertigungseinzelkosten_pro_einheit", "Fertigungseinzelkosten"),
        (("bearbeitungszeit",), "Produktionsdurchlaufzeit", "bearbeitungszeit", "Bearbeitungszeit"),
        (("liegezeit",), "Produktionsdurchlaufzeit", "liegezeit", "Liegezeit"),
        (("gesamtenergieverbrauch", "energieverbrauch"),
         "Anteil erneuerbarer Energien", "gesamtenergieverbrauch", "Gesamtenergieverbrauch"),
    ]
    direkte_definitionen = [
        (("produktionsdurchlaufzeit", "durchlaufzeit"), "Produktionsdurchlaufzeit"),
        (("anteil erneuerbarer energien", "anteil erneuerbarer energie"),
         "Anteil erneuerbarer Energien"),
        (("qualitaetsrate", "qualitätsrate"), "Qualitätsrate"),
        (("fertigungskosten",), "Fertigungskosten"),
    ]

    for aliases, kennzahl, faktor, bezeichnung in faktor_definitionen:
        if not any(_alias_im_text(normiert, alias) for alias in aliases):
            continue
        wert = _wert_nahe_alias(text, aliases)
        if wert is None or wert <= 0:
            continue
        ziel_alt = alt_name
        if not ziel_alt:
            kandidaten = [
                alt["name"] for alt in st.session_state.alternativen
                if ist_formel_kennzahl(kennzahl, alt["datenoption"])
            ]
            if len(kandidaten) == 1:
                ziel_alt = kandidaten[0]
        alternative = alternative_nach_name(ziel_alt or "")
        if not alternative or not ist_formel_kennzahl(kennzahl, alternative["datenoption"]):
            continue
        _setze_modus(ziel_alt, kennzahl, "berechnen")
        _faktoren(ziel_alt, kennzahl)[faktor] = float(wert)
        _aktualisiere_berechneten_wert(ziel_alt, kennzahl)
        meldungen.append(f"{bezeichnung} für {ziel_alt}: {_tabellenwert(wert)}")

    for aliases, kennzahl in direkte_definitionen:
        if not any(_alias_im_text(normiert, alias) for alias in aliases):
            continue
        wert = _wert_nahe_alias(text, aliases)
        if wert is None or not _wert_ist_plausibel(kennzahl, wert):
            continue
        ziel_alt = alt_name
        if not ziel_alt:
            kandidaten = [
                alt["name"] for alt in st.session_state.alternativen
                if kennzahl in aktive_kennzahlen_alternative(alt)
            ]
            if len(kandidaten) == 1:
                ziel_alt = kandidaten[0]
        if not ziel_alt or not alternative_nach_name(ziel_alt):
            continue
        _speichere_direktwert(ziel_alt, kennzahl, wert)
        meldungen.append(f"{kennzahl} für {ziel_alt}: {_tabellenwert(wert)}")

    if not meldungen:
        return None
    return "Gespeichert: " + "; ".join(meldungen) + "."



def _phase3_interpretationskontext(aktuelle_aktion=None) -> dict:
    """Erstellt den fachlich zulässigen Kontext für die semantische Eingabeanalyse.

    Das Sprachmodell erhält ausschließlich Bezeichnungen und Eingabestrukturen. Es
    berechnet keine Kennzahlen und entscheidet nicht über die Gültigkeit der Werte.
    """
    alternativen = []
    for alternative in st.session_state.alternativen:
        datenoption = alternative["datenoption"]
        aktive = aktive_kennzahlen_alternative(alternative)
        berechenbare = {}
        for kennzahl in aktive:
            if not ist_formel_kennzahl(kennzahl, datenoption):
                continue
            berechenbare[kennzahl] = [
                {
                    "schluessel": schluessel,
                    "bezeichnung": bezeichnung,
                    "einheit": einheit,
                }
                for schluessel, bezeichnung, einheit
                in faktoren_fuer(kennzahl, datenoption)
            ]
        alternativen.append(
            {
                "name": alternative["name"],
                "datenoption": datenoption,
                "aktive_kennzahlen": aktive,
                "berechenbare_kennzahlen": berechenbare,
            }
        )

    aktuelle_abfrage = None
    if aktuelle_aktion:
        art, alt_name, kennzahl, faktor = aktuelle_aktion
        aktuelle_abfrage = {
            "art": art,
            "alternative": alt_name,
            "kennzahl": kennzahl,
            "naechster_faktor": faktor,
        }
    return {
        "alternativen": alternativen,
        "aktuelle_abfrage": aktuelle_abfrage,
    }


def _interpretiere_phase3_semantisch(eingabe: str, aktuelle_aktion=None) -> Optional[dict]:
    """Interpretiert freie Eingaben, ohne Werte zu berechnen oder zu speichern.

    Die Funktion wird als zusätzliche Verständnisebene eingesetzt. Fällt der
    Modellaufruf aus oder bleibt die Aussage unklar, greift anschließend weiterhin
    die bestehende regelbasierte Verarbeitung.
    """
    kontext = _phase3_interpretationskontext(aktuelle_aktion)
    werkzeug = {
        "name": "strukturiere_dateneingabe",
        "description": (
            "Extrahiert direkte Kennzahlenwerte und Teilwerte zur Berechnung aus "
            "einer freien Nutzereingabe. Es dürfen keine Werte berechnet werden."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "angaben": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "alternative": {
                                "type": "string",
                                "description": "Exakter Name einer Alternative aus dem Kontext.",
                            },
                            "art": {
                                "type": "string",
                                "enum": [
                                    "direkter_kennzahlenwert",
                                    "berechnungsfaktor",
                                ],
                            },
                            "kennzahl": {
                                "type": "string",
                                "description": "Exakter Kennzahlenname aus dem Kontext.",
                            },
                            "wertname": {
                                "type": "string",
                                "description": (
                                    "Bei einem Berechnungsfaktor der exakte "
                                    "Faktorschlüssel aus dem Kontext, sonst leer."
                                ),
                            },
                            "wert": {"type": "number"},
                        },
                        "required": [
                            "alternative",
                            "art",
                            "kennzahl",
                            "wertname",
                            "wert",
                        ],
                    },
                },
                "mehrdeutig": {"type": "boolean"},
                "rueckfrage": {
                    "type": "string",
                    "description": (
                        "Kurze Rückfrage, wenn eine eindeutige Zuordnung nicht "
                        "möglich ist. Sonst leer."
                    ),
                },
            },
            "required": ["angaben", "mehrdeutig", "rueckfrage"],
        },
    }
    system = f"""Sie strukturieren ausschließlich Dateneingaben für Phase 3 einer
Anwendung zur Konfiguration globaler Produktionsnetzwerke.

Regeln:
- Extrahieren Sie nur ausdrücklich genannte Zahlenwerte.
- Berechnen, addieren, dividieren oder schätzen Sie keine Werte.
- Ordnen Sie Angaben nur den im Kontext enthaltenen Alternativen, Kennzahlen und
  Berechnungsfaktoren zu.
- Verwenden Sie für Alternative, Kennzahl und wertname exakt die Bezeichnungen
  beziehungsweise Faktorschlüssel aus dem Kontext.
- Ein fertiger Istwert einer Kennzahl erhält die Art direkter_kennzahlenwert.
- Ein Teilwert für eine hinterlegte Formel erhält die Art berechnungsfaktor.
- Korrekturen werden genauso wie neue Angaben extrahiert; der neue Wert ist maßgeblich.
- Mehrere Angaben in einem Satz werden als mehrere Elemente ausgegeben.
- Die aktuelle Abfrage darf zur Auflösung kurzer Antworten wie '7200 Euro' genutzt werden.
- Ist eine Zuordnung nicht eindeutig, geben Sie keine Vermutung aus, setzen Sie
  mehrdeutig auf true und formulieren Sie genau eine kurze Rückfrage auf Deutsch.

Zulässiger Kontext:
{json.dumps(kontext, ensure_ascii=False)}"""
    try:
        antwort = client.messages.create(
            model=MODELL,
            max_tokens=500,
            thinking={"type": "disabled"},
            system=system,
            messages=[{"role": "user", "content": eingabe}],
            tools=[werkzeug],
            tool_choice={"type": "tool", "name": "strukturiere_dateneingabe"},
        )
    except Exception:
        return None

    for block in antwort.content:
        if (
            getattr(block, "type", None) == "tool_use"
            and getattr(block, "name", None) == "strukturiere_dateneingabe"
        ):
            daten = getattr(block, "input", None)
            return daten if isinstance(daten, dict) else None
    return None


def _alternative_aus_interpretation(
    bezeichnung: str,
    aktuelle_aktion=None,
) -> Optional[str]:
    bezeichnung_norm = _norm_text(bezeichnung)
    treffer = []
    for alternative in st.session_state.alternativen:
        if bezeichnung_norm in {
            _norm_text(alternative["name"]),
            _norm_text(alternative["datenoption"]),
        }:
            treffer.append(alternative["name"])
    if len(set(treffer)) == 1:
        return treffer[0]
    if not bezeichnung_norm and aktuelle_aktion:
        return aktuelle_aktion[1]
    return None


def _kennzahl_aus_interpretation(
    bezeichnung: str,
    alt_name: str,
) -> Optional[str]:
    alternative = alternative_nach_name(alt_name)
    if not alternative:
        return None
    bezeichnung_norm = _norm_text(bezeichnung)
    treffer = [
        kennzahl
        for kennzahl in aktive_kennzahlen_alternative(alternative)
        if _norm_text(kennzahl) == bezeichnung_norm
    ]
    return treffer[0] if len(treffer) == 1 else None


def _faktor_aus_interpretation(
    kennzahl: str,
    datenoption: str,
    wertname: str,
) -> Optional[str]:
    wertname_norm = _norm_text(wertname)
    for schluessel, bezeichnung, _ in faktoren_fuer(kennzahl, datenoption):
        if wertname_norm in {_norm_text(schluessel), _norm_text(bezeichnung)}:
            return schluessel

    # Wenige fachlich eindeutige Synonyme erhöhen die Robustheit, ohne die
    # Berechnungslogik oder die in der Arbeit dokumentierten Datenstrukturen zu ändern.
    synonyme = {
        "fek": "fertigungseinzelkosten_pro_einheit",
        "fertigungseinzelkosten": "fertigungseinzelkosten_pro_einheit",
        "wartezeit": "liegezeit",
        "energiebedarf": "gesamtenergieverbrauch",
    }
    kandidat = synonyme.get(wertname_norm)
    erlaubte = {
        schluessel
        for schluessel, _, _ in faktoren_fuer(kennzahl, datenoption)
    }
    return kandidat if kandidat in erlaubte else None


def _wende_semantische_phase3_angaben_an(
    interpretation: Optional[dict],
    aktuelle_aktion=None,
) -> Optional[str]:
    if not isinstance(interpretation, dict):
        return None

    meldungen = []
    for angabe in interpretation.get("angaben") or []:
        if not isinstance(angabe, dict):
            continue
        alt_name = _alternative_aus_interpretation(
            str(angabe.get("alternative") or ""),
            aktuelle_aktion,
        )
        if not alt_name:
            continue
        alternative = alternative_nach_name(alt_name)
        if not alternative:
            continue
        kennzahl = _kennzahl_aus_interpretation(
            str(angabe.get("kennzahl") or ""),
            alt_name,
        )
        if not kennzahl:
            continue
        try:
            wert = float(angabe.get("wert"))
        except (TypeError, ValueError):
            continue

        art = str(angabe.get("art") or "")
        if art == "direkter_kennzahlenwert":
            if not _wert_ist_plausibel(kennzahl, wert):
                continue
            _speichere_direktwert(alt_name, kennzahl, wert)
            meldungen.append(
                f"{kennzahl} für {alt_name}: {_tabellenwert(wert)}"
            )
            continue

        if art != "berechnungsfaktor":
            continue
        datenoption = alternative["datenoption"]
        if not ist_formel_kennzahl(kennzahl, datenoption) or wert <= 0:
            continue
        faktor = _faktor_aus_interpretation(
            kennzahl,
            datenoption,
            str(angabe.get("wertname") or ""),
        )
        if not faktor:
            continue
        _setze_modus(alt_name, kennzahl, "berechnen")
        _faktoren(alt_name, kennzahl)[faktor] = wert
        _aktualisiere_berechneten_wert(alt_name, kennzahl)
        info = faktor_information(kennzahl, faktor, datenoption)
        bezeichnung = info[0] if info else faktor
        meldungen.append(
            f"{bezeichnung} für {alt_name}: {_tabellenwert(wert)}"
        )

    if meldungen:
        prefix = "Gespeichert: " + "; ".join(meldungen) + "."
        return _naechste_frage_oder_bestaetigung(prefix)

    if interpretation.get("mehrdeutig"):
        rueckfrage = str(interpretation.get("rueckfrage") or "").strip()
        if rueckfrage:
            return rueckfrage
    return None


def _naechste_frage_oder_bestaetigung(prefix: str = "") -> str:
    aktion = _naechste_phase3_aktion()
    if aktion:
        frage = _frage_fuer_aktion(aktion)
        return f"{prefix} {frage}".strip()
    return (
        f"{prefix} Alle erforderlichen Werte liegen nun vor. Bitte prüfen Sie "
        "die vollständig ausgefüllte Tabelle und bestätigen Sie, ob die Angaben "
        "korrekt sind und mit der Berechnung fortgefahren werden kann."
    ).strip()


def verarbeite_phase3_eingabe(eingabe: str):
    aktuelle_aktion = _naechste_phase3_aktion()
    benannte_angaben = _versuche_benannte_aenderung(eingabe, aktuelle_aktion)
    if benannte_angaben:
        _assistententext_hinzufuegen(
            _naechste_frage_oder_bestaetigung(benannte_angaben)
        )
        return

    # Eine eindeutige Bestätigung wird ohne Modellaufruf verarbeitet. Korrekturen
    # und sonstige freie Formulierungen werden anschließend semantisch interpretiert.
    if aktuelle_aktion is None and _ist_bestaetigung(eingabe):
        st.session_state.phase = 4
        st.session_state.basis_ergebnis = None
        _assistententext_hinzufuegen(
            "Vielen Dank. Die bestätigte Datengrundlage wird nun mathematisch bewertet."
        )
        return

    interpretation = _interpretiere_phase3_semantisch(eingabe, aktuelle_aktion)
    semantische_antwort = _wende_semantische_phase3_angaben_an(
        interpretation,
        aktuelle_aktion,
    )
    if semantische_antwort:
        _assistententext_hinzufuegen(semantische_antwort)
        return

    if aktuelle_aktion is None:
        _assistententext_hinzufuegen(
            "Bitte bestätigen Sie die Tabelle oder nennen Sie die zu korrigierende "
            "Kennzahl beziehungsweise den zu korrigierenden Teilwert mit dem neuen Wert."
        )
        return

    art, alt_name, kennzahl, faktor = aktuelle_aktion
    alternative = alternative_nach_name(alt_name) or {}
    datenoption = alternative.get("datenoption", "")
    normiert = _norm_text(eingabe)
    zahlen = _deutsche_zahlen_lesen(eingabe)

    if art == "formel":
        direkte_signale = ("direkt", "rohwert", "istwert")
        kpi_aliasse = {
            "Fertigungskosten": ("fertigungskosten",),
            "Produktionsdurchlaufzeit": ("produktionsdurchlaufzeit", "durchlaufzeit"),
            "Anteil erneuerbarer Energien": (
                "anteil erneuerbarer energien",
                "anteil erneuerbarer energie",
            ),
        }.get(kennzahl, ())
        direkte_eingabe = any(signal in normiert for signal in direkte_signale)
        direkte_eingabe = direkte_eingabe or any(
            _alias_im_text(normiert, alias) for alias in kpi_aliasse
        )
        if direkte_eingabe and zahlen:
            wert = zahlen[-1]
            if not _wert_ist_plausibel(kennzahl, wert):
                _assistententext_hinzufuegen(
                    "Der genannte Istwert ist nicht plausibel. " + _frage_fuer_aktion(aktuelle_aktion)
                )
                return
            _speichere_direktwert(alt_name, kennzahl, wert)
            _assistententext_hinzufuegen(_naechste_frage_oder_bestaetigung())
            return

        fehlende = [
            schluessel
            for schluessel, _, _ in faktoren_fuer(kennzahl, datenoption)
            if schluessel not in _faktoren(alt_name, kennzahl)
        ]
        if not zahlen:
            _assistententext_hinzufuegen(
                "Die Eingabe konnte nicht eindeutig als Zahlenwert verarbeitet werden. "
                + _frage_fuer_aktion(aktuelle_aktion)
            )
            return
        _setze_modus(alt_name, kennzahl, "berechnen")
        for schluessel, wert in zip(fehlende, zahlen):
            if wert > 0:
                _faktoren(alt_name, kennzahl)[schluessel] = float(wert)
        _aktualisiere_berechneten_wert(alt_name, kennzahl)
        _assistententext_hinzufuegen(_naechste_frage_oder_bestaetigung())
        return

    wert = _deutsche_zahl_lesen(eingabe)
    if not _wert_ist_plausibel(kennzahl, wert):
        _assistententext_hinzufuegen(
            "Die Eingabe konnte nicht eindeutig als plausibler Zahlenwert verarbeitet werden. "
            + _frage_fuer_aktion(aktuelle_aktion)
        )
        return
    _speichere_direktwert(alt_name, kennzahl, float(wert))
    _assistententext_hinzufuegen(_naechste_frage_oder_bestaetigung())


def _beschreibungen_fuer_prompt() -> str:
    phase = st.session_state.phase
    teile = []
    if phase == 0:
        teile.append(
            "Phasenbeschreibungen: "
            + json.dumps(
                {nummer: daten["beschreibung"] for nummer, daten in PHASEN.items()},
                ensure_ascii=False,
            )
        )
    if phase == 1:
        teile.append(
            "Szenariobeschreibungen: "
            + json.dumps(SZENARIO_BESCHREIBUNGEN, ensure_ascii=False)
        )
    if phase == 2:
        teile.append(
            "Beschreibungen der Leistungsdimensionen: "
            + json.dumps(DIMENSION_BESCHREIBUNGEN, ensure_ascii=False)
        )
    return "\n".join(teile)


def baue_system_prompt() -> str:
    phase = st.session_state.phase
    kontext = ""
    if st.session_state.vorlaeufige_typen:
        kontext += (
            "\nAusgewählte Szenariotypen: "
            + ", ".join(st.session_state.vorlaeufige_typen)
            + "."
        )
    if st.session_state.vorlaeufige_baureihe:
        kontext += f" Betroffene Baureihe: {st.session_state.vorlaeufige_baureihe}."
    if st.session_state.alternativen:
        kontext += "\nDefinierte Alternativen: " + json.dumps(
            st.session_state.alternativen,
            ensure_ascii=False,
        )

    if phase == 4 and st.session_state.basis_ergebnis:
        erg = st.session_state.basis_ergebnis
        kontext += "\nBerechnungsergebnis: " + json.dumps(
            {
                "gewichte": erg["gewichte"],
                "dim_scores": erg["dim_scores"],
                "gesamtpunktzahlen": erg["nutzwerte"],
                "raenge": erg["raenge"],
                "empfehlung": erg["empfehlung"],
            },
            ensure_ascii=False,
        )
    if phase == 5:
        if st.session_state.basis_ergebnis:
            kontext += (
                f"\nInitiale Empfehlung: {st.session_state.basis_ergebnis['empfehlung']}."
            )
        if st.session_state.sensitivitaet_ergebnis:
            erg = st.session_state.sensitivitaet_ergebnis
            kontext += "\nLetztes Sensitivitätsergebnis: " + json.dumps(
                {
                    "gewichte": erg["gewichte"],
                    "gesamtpunktzahlen": erg["nutzwerte"],
                    "raenge": erg["raenge"],
                    "empfehlung": erg["empfehlung"],
                },
                ensure_ascii=False,
            )
    if phase == 6 and st.session_state.basis_ergebnis:
        erg = st.session_state.basis_ergebnis
        kontext += "\nAbschlussergebnis: " + json.dumps(
            {
                "gewichte": erg["gewichte"],
                "dim_scores": erg["dim_scores"],
                "gesamtpunktzahlen": erg["nutzwerte"],
                "raenge": erg["raenge"],
                "empfehlung": erg["empfehlung"],
                "robustheit": st.session_state.robustheit,
            },
            ensure_ascii=False,
        )

    if phase == 0:
        phasenanweisung = (
            "Der Einstiegstext und der Phasenüberblick wurden bereits angezeigt. "
            "Beantworten Sie Rückfragen kurz. Wenn die nutzende Person beginnen möchte, "
            "rufen Sie naechste_phase auf."
        )
    elif phase == 1:
        if not st.session_state.vorlaeufige_typen:
            phasenanweisung = (
                "Die auswählbaren Szenariotypen wurden bereits einmalig als Stichpunkte "
                "angezeigt. Beantworten Sie Rückfragen kurz und beschreiben Sie ein "
                "Szenario nur auf ausdrückliche Nachfrage. Fragen Sie ansonsten direkt "
                "nach der Auswahl und speichern Sie diese mit setze_szenario_typen."
            )
        elif (
            any("Verlagerung" in typ for typ in st.session_state.vorlaeufige_typen)
            and not st.session_state.vorlaeufige_baureihe
        ):
            phasenanweisung = (
                "Fragen Sie in genau einem kurzen Satz nach der betroffenen Baureihe. "
                "Sobald sie eindeutig genannt wurde, rufen Sie setze_baureihe auf."
            )
        else:
            phasenanweisung = (
                "Fragen Sie kurz nach mindestens zwei konkreten Handlungsalternativen. "
                f"Verfügbare Datengrundlagen: {', '.join(VERFUEGBARE_DATENOPTIONEN)}. "
                "Standort C darf angeboten werden. Erläutern Sie Ausprägungen nur auf "
                "Nachfrage. Wenn alle Angaben vorliegen, rufen Sie "
                "finalisiere_alternativen auf."
            )
    elif phase == 2:
        phasenanweisung = (
            "Die Gewichtung wird ausschließlich über die sichtbaren Schieberegler der "
            "Benutzeroberfläche eingestellt; ihre Summe beträgt 100 Prozent. Fordern Sie "
            "niemals dazu auf, Gewichtungswerte im Chat einzugeben. Beantworten Sie nur "
            "Rückfragen zu den Leistungsdimensionen kurz. Die Bestätigung zum Fortfahren "
            "wird von der Anwendung selbst verarbeitet."
        )
    elif phase == 4:
        phasenanweisung = (
            "Die Anwendung zeigt Normalisierung, Dimensionswerte und Gesamtpunktzahlen. "
            "Beantworten Sie Rückfragen als Fließtext. Bei Bestätigung rufen Sie "
            "naechste_phase auf."
        )
    elif phase == 5:
        phasenanweisung = (
            "Die nutzende Person variiert die Gewichtungen in der Oberfläche. "
            "Nach ihren Versuchen soll sie das Ergebnis als robust, nicht robust "
            "oder unklar einschätzen und Beobachtungen nennen. Eine ausdrückliche "
            "Angabe, dass keine Auffälligkeiten festgestellt wurden, ist eine gültige "
            "Beobachtung und muss akzeptiert werden. Speichern Sie Einschätzung und "
            "Beobachtungen mit speichere_robustheit. Wenn keine Auffälligkeiten "
            "vorliegen, verwenden Sie als Begründung 'Keine Auffälligkeiten festgestellt.'."
        )
    else:
        phasenanweisung = (
            "Formulieren Sie eine kurze Abschlusszusammenfassung in höchstens zwei "
            "Absätzen. Nennen Sie Vorgehen, Ranking, Empfehlung und die Einordnung "
            "der Robustheit. Verwenden Sie ausschließlich Zahlen aus dem Kontext."
        )

    return f"""Sie sind ein professioneller Entscheidungsassistent für die Konfiguration globaler Produktionsnetzwerke in der Off-Highway-Motorenbranche.

Verbindliche Regeln:
- Sprechen Sie die nutzende Person konsequent mit "Sie" an.
- Verwenden Sie keine Emojis.
- Schreiben Sie sachlich, professionell und präzise.
- Formulieren Sie grundsätzlich höchstens zwei kurze Sätze, außer eine ausführliche Erklärung wird ausdrücklich verlangt.
- Beantworten Sie Rückfragen als Fließtext und nicht als Stichpunkte.
- Sämtliche numerischen Berechnungen erfolgen ausschließlich im Anwendungscode.
- Berechnen oder schätzen Sie keine Normwerte, Dimensionswerte, Gesamtpunktzahlen oder Rangfolgen.
- Der Prozess wird streng sequenziell durchlaufen. Fordern Sie niemals zum Zurückspringen auf.
- Bleiben Sie in der aktuellen Phase.
- Erklären Sie Phasen, Szenarien und Leistungsdimensionen nur auf Nachfrage.

Aktuelle Phase {phase}: {PHASEN[phase]['titel']}
{phasenanweisung}
{kontext}
{_beschreibungen_fuer_prompt()}
"""


def tool_definitionen() -> list[dict]:
    werkzeuge: list[dict] = []
    phase = st.session_state.phase
    if phase in (0, 4):
        werkzeuge.append(
            {
                "name": "naechste_phase",
                "description": "Wechselt nach erfüllten Bedingungen zur nächsten Phase.",
                "input_schema": {"type": "object", "properties": {}},
            }
        )
    if phase == 1:
        if not st.session_state.vorlaeufige_typen:
            werkzeuge.append(
                {
                    "name": "setze_szenario_typen",
                    "description": "Speichert einen oder mehrere ausgewählte Szenariotypen.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "typen": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1,
                            }
                        },
                        "required": ["typen"],
                    },
                }
            )
        elif (
            any("Verlagerung" in typ for typ in st.session_state.vorlaeufige_typen)
            and not st.session_state.vorlaeufige_baureihe
        ):
            werkzeuge.append(
                {
                    "name": "setze_baureihe",
                    "description": "Speichert die bei einer Verlagerung betrachtete Baureihe.",
                    "input_schema": {
                        "type": "object",
                        "properties": {"baureihe": {"type": "string"}},
                        "required": ["baureihe"],
                    },
                }
            )
        else:
            werkzeuge.append(
                {
                    "name": "finalisiere_alternativen",
                    "description": "Speichert mindestens zwei vollständig definierte Handlungsalternativen.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "alternativen": {
                                "type": "array",
                                "minItems": 2,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "szenario_typ": {"type": "string"},
                                        "datenoption": {"type": "string"},
                                    },
                                    "required": ["name", "szenario_typ", "datenoption"],
                                },
                            }
                        },
                        "required": ["alternativen"],
                    },
                }
            )
    if phase == 5:
        werkzeuge.append(
            {
                "name": "speichere_robustheit",
                "description": "Speichert die abschließende Robustheitsbewertung.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "bewertung": {
                            "type": "string",
                            "enum": ["robust", "nicht robust", "unklar"],
                        },
                        "begruendung": {
                            "type": "string",
                            "description": (
                                "Beobachtungen aus der Sensitivitätsanalyse. "
                                "Wenn keine Auffälligkeiten vorliegen, ist ausdrücklich "
                                "'Keine Auffälligkeiten festgestellt.' zu verwenden."
                            ),
                        },
                    },
                    "required": ["bewertung"],
                },
            }
        )
    return werkzeuge


def fuehre_werkzeug_aus(aufruf) -> str:
    if aufruf.name == "naechste_phase":
        phase = st.session_state.phase
        if phase == 0:
            st.session_state.phase = 1
            st.session_state.phase1_gestartet = False
        elif phase == 2:
            st.session_state.phase = 3
            st.session_state.phase3_gestartet = False
        elif phase == 4:
            if st.session_state.basis_ergebnis is None:
                return "Die Berechnung muss zunächst vollständig vorliegen."
            st.session_state.phase = 5
        return f"Phase gewechselt. Aktuelle Phase: {st.session_state.phase}."

    if aufruf.name == "setze_szenario_typen":
        typen = list(dict.fromkeys(aufruf.input.get("typen") or []))
        gueltige = [typ for typ in typen if typ in SZENARIO_TYPEN]
        if not gueltige:
            return "Es wurde kein gültiger Szenariotyp angegeben."
        st.session_state.vorlaeufige_typen = gueltige
        st.session_state.vorlaeufige_baureihe = ""
        return "Die Szenariotypen wurden gespeichert. Fahren Sie mit den noch erforderlichen Angaben fort."

    if aufruf.name == "setze_baureihe":
        baureihe = str(aufruf.input.get("baureihe") or "").strip()
        if not baureihe:
            return "Es wurde keine gültige Baureihe angegeben."
        st.session_state.vorlaeufige_baureihe = baureihe
        return "Die Baureihe wurde gespeichert. Definieren Sie nun mindestens zwei Alternativen."

    if aufruf.name == "finalisiere_alternativen":
        rohe_alternativen = aufruf.input.get("alternativen") or []
        bereinigt = []
        namen = set()
        for roh in rohe_alternativen:
            if not isinstance(roh, dict):
                continue
            name = str(roh.get("name") or "").strip()
            typ = str(roh.get("szenario_typ") or "").strip()
            datenoption = str(roh.get("datenoption") or "").strip()
            if (
                not name
                or name in namen
                or typ not in st.session_state.vorlaeufige_typen
                or datenoption not in VERFUEGBARE_DATENOPTIONEN
            ):
                continue
            namen.add(name)
            bereinigt.append(
                {"name": name, "szenario_typ": typ, "datenoption": datenoption}
            )
        if len(bereinigt) < 2:
            return "Es werden mindestens zwei gültige und eindeutig benannte Alternativen benötigt."
        fehlende_typen = [
            typ for typ in st.session_state.vorlaeufige_typen
            if typ not in {alt["szenario_typ"] for alt in bereinigt}
        ]
        if len(st.session_state.vorlaeufige_typen) > 1 and fehlende_typen:
            return "Jeder ausgewählte Szenariotyp muss durch mindestens eine Alternative vertreten sein."

        st.session_state.alternativen = bereinigt
        st.session_state.baureihe = st.session_state.vorlaeufige_baureihe
        st.session_state.gewichte = initiale_gewichte()
        setze_slider_aus_gewichten(st.session_state.gewichte, "basis")
        st.session_state.nutzer_werte = {}
        st.session_state.nutzer_quelle = {}
        st.session_state.phase3_faktoren = {}
        st.session_state.phase3_modus = {}
        st.session_state.basis_ergebnis = None
        st.session_state.sensitivitaet_gewichte = {}
        st.session_state.sensitivitaet_ergebnis = None
        st.session_state.sensitivitaetslaeufe = []
        st.session_state.robustheit = None
        st.session_state.phase3_gestartet = False
        st.session_state.phase6_gestartet = False
        st.session_state.phase = 2
        return "Die Entscheidungssituation ist vollständig definiert. Phase 2 ist aktiv."

    if aufruf.name == "speichere_robustheit":
        st.session_state.robustheit = {
            "bewertung": str(aufruf.input.get("bewertung") or "unklar"),
            "begruendung": str(aufruf.input.get("begruendung") or "").strip(),
        }
        st.session_state.phase = 6
        st.session_state.phase6_gestartet = False
        return "Die Robustheitsbewertung wurde gespeichert."

    return "Unbekanntes Werkzeug."


def fuehre_dialog_runde():
    while True:
        werkzeuge = tool_definitionen()
        anfrage = {
            "model": MODELL,
            "max_tokens": MAX_TOKENS,
            "thinking": {"type": "disabled"},
            "system": baue_system_prompt(),
            "messages": st.session_state.messages,
        }
        if werkzeuge:
            anfrage["tools"] = werkzeuge
        try:
            antwort = client.messages.create(**anfrage)
        except Exception as fehler:
            st.error(
                "Die Verbindung zum Sprachmodell ist fehlgeschlagen. "
                f"Technischer Fehlertyp: {type(fehler).__name__}."
            )
            return

        st.session_state.messages.append(
            {"role": "assistant", "content": antwort.content}
        )
        tool_aufrufe = [
            block for block in antwort.content
            if getattr(block, "type", None) == "tool_use"
        ]
        if not tool_aufrufe:
            return

        phase_vor_werkzeugen = st.session_state.phase
        ergebnisse = []
        for aufruf in tool_aufrufe:
            ergebnisse.append(
                {
                    "type": "tool_result",
                    "tool_use_id": aufruf.id,
                    "content": fuehre_werkzeug_aus(aufruf),
                }
            )
        st.session_state.messages.append({"role": "user", "content": ergebnisse})

        # Nach einem Phasenwechsel wird kein zweiter Modelltext erzeugt. Der
        # Einstieg der neuen Phase wird beim nächsten Rerun einmalig angezeigt.
        if st.session_state.phase != phase_vor_werkzeugen:
            return


def _bestaetigt_gewichtung(eingabe: str) -> bool:
    """Erkennt nur eine Bestätigung zum Fortfahren, keine Gewichtseingaben."""
    text = re.sub(r"[^a-zäöüß ]", " ", eingabe.lower())
    text = re.sub(r"\s+", " ", text).strip()
    signale = (
        "weiter",
        "fortfahren",
        "weitergehen",
        "weiter machen",
        "weitermachen",
        "gewichtung übernehmen",
        "gewichtung passt",
        "so passt es",
        "ist fertig",
        "bin fertig",
        "kann weitergehen",
        "kann weiter gehen",
    )
    return any(signal in text for signal in signale)


def _enthaelt_keine_auffaelligkeiten(eingabe: str) -> bool:
    """Erkennt Aussagen, dass im Sensitivitätstest keine Auffälligkeiten vorlagen."""
    text = eingabe.lower()
    signale = (
        "keine auffälligkeiten",
        "keine auffaelligkeiten",
        "nichts auffällig",
        "nichts auffaellig",
        "keine besonderheiten",
        "keine abweichungen",
        "keine veränderungen",
        "keine veraenderungen",
        "rangfolge blieb gleich",
        "empfehlung blieb gleich",
    )
    return any(signal in text for signal in signale)


def _robustheitsbewertung_aus_text(eingabe: str) -> Optional[str]:
    """Liest eine eindeutige Robustheitsbewertung aus freiem Text."""
    text = re.sub(r"[^a-zäöüß ]", " ", eingabe.lower())
    text = re.sub(r"\s+", " ", text).strip()

    if re.search(
        r"\bnicht(?: besonders)?\s+robust\b|\bwenig\s+robust\b|"
        r"\bnicht\s+stabil\b|\binstabil\b|\bsensitiv\b",
        text,
    ):
        return "nicht robust"
    if re.search(
        r"\bunklar\b|\bnicht eindeutig\b|\bnicht beurteilbar\b|"
        r"\bkann ich nicht beurteilen\b",
        text,
    ):
        return "unklar"
    if re.search(r"\brobust\b|\bstabil\b", text):
        return "robust"
    return None


def _verarbeite_phase5_eingabe(eingabe: str) -> bool:
    """Verarbeitet eindeutige Robustheitsaussagen zuverlässig im Anwendungscode.

    Rückgabe True bedeutet, dass die Eingabe vollständig behandelt wurde.
    Mehrdeutige Rückfragen werden weiterhin an das Sprachmodell übergeben.
    """
    bewertung = _robustheitsbewertung_aus_text(eingabe)
    keine_auffaelligkeiten = _enthaelt_keine_auffaelligkeiten(eingabe)

    if keine_auffaelligkeiten:
        st.session_state.robustheit_beobachtung_vorlaeufig = (
            "Keine Auffälligkeiten festgestellt."
        )

    if bewertung is None:
        if keine_auffaelligkeiten:
            _assistententext_hinzufuegen(
                "Es wurden keine Auffälligkeiten festgestellt. Bewerten Sie das "
                "Ergebnis bitte noch als robust, nicht robust oder unklar."
            )
            return True
        return False

    begruendung = st.session_state.get(
        "robustheit_beobachtung_vorlaeufig",
        "",
    )
    if keine_auffaelligkeiten:
        begruendung = "Keine Auffälligkeiten festgestellt."
    elif not begruendung:
        begruendung = eingabe.strip()

    st.session_state.robustheit = {
        "bewertung": bewertung,
        "begruendung": begruendung,
    }
    st.session_state.robustheit_beobachtung_vorlaeufig = ""
    st.session_state.phase = 6
    st.session_state.phase6_gestartet = False
    return True


def _uebernehme_slider_gewichtung():
    """Überträgt die aktuell sichtbaren Reglerwerte sicher in den Sitzungsspeicher."""
    st.session_state.gewichte = {
        dimension: st.session_state.get(
            f"basis_{dimension}",
            round(st.session_state.gewichte.get(dimension, 0.0) * 100),
        ) / 100.0
        for dimension in ALLE_DIMENSIONEN
    }


def chat_eingabe(platzhalter: str = "Ihre Antwort"):
    eingabe = st.chat_input(platzhalter)
    if not eingabe:
        return
    st.session_state.messages.append({"role": "user", "content": eingabe})
    with st.chat_message("user"):
        st.markdown(eingabe)

    if st.session_state.phase == 2 and _bestaetigt_gewichtung(eingabe):
        _uebernehme_slider_gewichtung()
        st.session_state.phase = 3
        st.session_state.phase3_gestartet = False
    elif st.session_state.phase == 3:
        verarbeite_phase3_eingabe(eingabe)
    elif st.session_state.phase == 5 and _verarbeite_phase5_eingabe(eingabe):
        pass
    else:
        with st.spinner("Antwort wird erstellt"):
            fuehre_dialog_runde()
    st.rerun()


for schluessel, standard in [
    ("phase", 0),
    ("messages", []),
    ("vorlaeufige_typen", []),
    ("vorlaeufige_baureihe", ""),
    ("baureihe", ""),
    ("alternativen", []),
    ("gewichte", initiale_gewichte()),
    ("nutzer_werte", {}),
    ("nutzer_quelle", {}),
    ("phase3_faktoren", {}),
    ("phase3_modus", {}),
    ("basis_ergebnis", None),
    ("sensitivitaet_gewichte", {}),
    ("sensitivitaet_ergebnis", None),
    ("sensitivitaetslaeufe", []),
    ("robustheit", None),
    ("robustheit_beobachtung_vorlaeufig", ""),
    ("phase0_gestartet", False),
    ("phase1_gestartet", False),
    ("phase3_gestartet", False),
    ("phase6_gestartet", False),
]:
    if schluessel not in st.session_state:
        st.session_state[schluessel] = standard


st.title("Konfiguration globaler Produktionsnetzwerke")

with st.sidebar:
    st.subheader("Phasen")
    for nummer in range(ANZAHL_PHASEN):
        if nummer < st.session_state.phase:
            status = "Abgeschlossen"
            klasse = "done"
        elif nummer == st.session_state.phase:
            status = "Aktuell"
            klasse = "current"
        else:
            status = "Offen"
            klasse = "open"
        st.markdown(
            f'<div class="phase-card {klasse}">'
            f'<div class="phase-title">{escape(PHASEN[nummer]["titel"])}</div>'
            f'<div class="phase-status">{status}</div></div>',
            unsafe_allow_html=True,
        )
    st.divider()
    if st.button("Neue Analyse starten", width="stretch"):
        for key in list(st.session_state.keys()):
            st.session_state.pop(key, None)
        st.rerun()

PHASE = st.session_state.phase
if st.session_state.alternativen:
    st.markdown(
        "**Alternativen:** "
        + ", ".join(alternative_namen())
        + (f"  **Baureihe:** {st.session_state.baureihe}" if st.session_state.baureihe else "")
    )


if PHASE == 0 and not st.session_state.phase0_gestartet:
    st.session_state.phase0_gestartet = True
    phasenzeilen = [
        f"| {PHASEN[nummer]['titel']} | {PHASEN[nummer]['kurz']} |"
        for nummer in range(1, ANZAHL_PHASEN)
    ]
    phasentabelle = (
        "| Phase | Inhalt |\n|---|---|\n" + "\n".join(phasenzeilen)
    )
    _assistententext_hinzufuegen(
        "Diese Anwendung unterstützt Sie dabei, Handlungsalternativen für globale "
        "Produktionsnetzwerke systematisch zu vergleichen und eine begründete "
        "Empfehlung abzuleiten. Auf Wunsch erläutere ich einzelne Phasen näher.\n\n"
        + phasentabelle
        + "\n\nMöchten Sie den Entscheidungsprozess beginnen?"
    )
    st.rerun()

if PHASE == 1 and not st.session_state.phase1_gestartet:
    st.session_state.phase1_gestartet = True
    szenarien_liste = "\n".join(f"- {typ}" for typ in SZENARIO_TYPEN)
    _assistententext_hinzufuegen(
        "Wählen Sie mindestens zwei Handlungsalternativen. Diese können "
        "unterschiedlichen Szenariotypen angehören oder unterschiedliche "
        "Ausprägungen desselben Szenariotyps darstellen. Auf Wunsch erläutert "
        "der Entscheidungsassistent einzelne Szenarien näher.\n\n"
        + szenarien_liste
    )
    st.rerun()

if PHASE == 3 and not st.session_state.phase3_gestartet:
    st.session_state.phase3_gestartet = True
    _assistententext_hinzufuegen(
        _naechste_frage_oder_bestaetigung()
    )
    st.rerun()

if PHASE == 6 and not st.session_state.phase6_gestartet:
    if st.session_state.basis_ergebnis is None:
        st.error("Es liegt kein Basis-Ergebnis vor.")
        st.stop()
    st.session_state.phase6_gestartet = True
    with st.spinner("Zusammenfassung wird erstellt"):
        st.session_state.messages.append(
            {
                "role": "user",
                "content": AUTO_MARKER + " Erstellen Sie die kurze Abschlusszusammenfassung.",
            }
        )
        fuehre_dialog_runde()
    st.rerun()


zeige_verlauf(letzte_assistentenantwort_auslassen=PHASE in (3, 6))



if PHASE == 2:
    st.divider()
    st.subheader(PHASEN[2]["titel"])
    st.markdown(
        "Passen Sie die Gewichtung der Leistungsdimensionen über die Schieberegler an. "
        "Die Summe beträgt stets 100 Prozent. Auf Wunsch erläutert der "
        "Entscheidungsassistent einzelne Leistungsdimensionen näher."
    )
    zeige_gewichts_slider(ALLE_DIMENSIONEN, "gewichte", "basis")
    st.markdown(
        "Stellen Sie die Gewichtungen ausschließlich über die Schieberegler ein. "
        "Wenn Sie fertig sind, schreiben Sie im Chat beispielsweise „weiter“."
    )

if PHASE == 3:
    st.divider()
    st.subheader(PHASEN[3]["titel"])
    with st.chat_message("assistant"):
        st.markdown(
            "In dieser Phase werden vorhandene Systemwerte und Ihre Eingaben "
            "zusammengeführt. Fehlende Kennzahlen können direkt angegeben oder aus "
            "Teilwerten berechnet werden; Korrekturen sind bis zur Bestätigung möglich."
        )
    zeige_tabelle_zentriert(datenuebersicht())
    zeige_aktuellen_bot_text()

if PHASE == 4:
    st.divider()
    st.subheader(PHASEN[4]["titel"])
    if offene_werte():
        st.error("Die Datengrundlage ist noch nicht vollständig.")
        st.stop()
    if st.session_state.basis_ergebnis is None:
        st.session_state.basis_ergebnis = rechne()
    erg = st.session_state.basis_ergebnis

    st.markdown("### 1. Normalisierung der Kennzahlenwerte")
    st.markdown(
        "Zunächst werden die Istwerte unter Berücksichtigung von Zielwert, "
        "Grenzwert und Wirkungsrichtung auf eine Skala von 0 bis 100 überführt."
    )
    zeilen = []
    aktive_nach_alt = aktive_kennzahlen_nach_alternative()
    for kennzahl in aktive_kennzahlen_gesamt():
        zeile = {
            "Leistungsdimension": KPIS[kennzahl]["dimension"],
            "Kennzahl": kennzahl,
            "Zielwert": KPIS[kennzahl]["zielwert"],
            "Grenzwert": KPIS[kennzahl]["grenzwert"],
        }
        for name in alternative_namen():
            zeile[f"Normwert {name}"] = (
                erg["normwerte"].get(name, {}).get(kennzahl, "Nicht relevant")
                if kennzahl in aktive_nach_alt.get(name, [])
                else "Nicht relevant"
            )
        zeilen.append(zeile)
    zeige_tabelle_zentriert(zeilen)

    st.markdown("### 2. Aggregation zu Werten der Leistungsdimensionen")
    st.markdown(
        "Anschließend werden die relevanten Normwerte innerhalb jeder "
        "Leistungsdimension arithmetisch gemittelt."
    )
    zeilen = []
    for dimension in ALLE_DIMENSIONEN:
        zeile = {
            "Leistungsdimension": dimension,
            "Gewichtung": f"{erg['gewichte'].get(dimension, 0) * 100:.0f} %",
        }
        for name in alternative_namen():
            zeile[name] = erg["dim_scores"].get(name, {}).get(
                dimension,
                "Nicht relevant",
            )
        zeilen.append(zeile)
    zeige_tabelle_zentriert(zeilen)

    st.markdown("### 3. Berechnung der Gesamtpunktzahlen")
    st.markdown(
        "Im letzten Schritt werden die Dimensionswerte mit den festgelegten "
        "Gewichtungen multipliziert und zu einer Gesamtpunktzahl addiert."
    )
    ranking = [
        {
            "Rang": erg["raenge"][name],
            "Alternative": name,
            "Gesamtpunktzahl": erg["nutzwerte"][name],
        }
        for name in sorted(erg["nutzwerte"], key=erg["nutzwerte"].get, reverse=True)
    ]
    zeige_tabelle_zentriert(ranking)
    st.info(f"Rechnerische Empfehlung: {erg['empfehlung']}")
    st.markdown(
        "Teilen Sie mir im Chat mit, wenn mit der Sensitivitätsanalyse fortgefahren werden kann."
    )

if PHASE == 5:
    st.divider()
    st.subheader(PHASEN[5]["titel"])
    if st.session_state.basis_ergebnis is None:
        st.error("Es liegt kein Basis-Ergebnis vor.")
        st.stop()
    st.markdown(
        "Variieren Sie die Gewichtungen und berechnen Sie das Ergebnis erneut. "
        "Die ursprüngliche Gewichtung und das Basis-Ergebnis bleiben unverändert gespeichert."
    )
    if not st.session_state.sensitivitaet_gewichte:
        st.session_state.sensitivitaet_gewichte = dict(
            st.session_state.basis_ergebnis["gewichte"]
        )
        setze_slider_aus_gewichten(st.session_state.sensitivitaet_gewichte, "sens")
    zeige_gewichts_slider(
        ALLE_DIMENSIONEN,
        "sensitivitaet_gewichte",
        "sens",
    )
    if st.button("Ergebnis neu berechnen"):
        ergebnis = rechne_mit_gewichten(st.session_state.sensitivitaet_gewichte)
        st.session_state.sensitivitaet_ergebnis = ergebnis
        st.session_state.sensitivitaetslaeufe.append(
            {
                "gewichte": deepcopy(ergebnis["gewichte"]),
                "nutzwerte": deepcopy(ergebnis["nutzwerte"]),
                "raenge": deepcopy(ergebnis["raenge"]),
                "empfehlung": ergebnis["empfehlung"],
            }
        )
        st.rerun()
    erg = st.session_state.sensitivitaet_ergebnis or st.session_state.basis_ergebnis
    zeige_tabelle_zentriert(
        [
            {
                "Rang": erg["raenge"][name],
                "Alternative": name,
                "Gesamtpunktzahl": erg["nutzwerte"][name],
            }
            for name in sorted(erg["nutzwerte"], key=erg["nutzwerte"].get, reverse=True)
        ]
    )
    st.info(f"Aktuelle Empfehlung im Sensitivitätstest: {erg['empfehlung']}")
    st.markdown(
        "Teilen Sie mir anschließend Ihre Einschätzung zur Robustheit mit und "
        "nennen Sie beobachtete Auffälligkeiten. Falls keine aufgetreten sind, "
        "können Sie ausdrücklich schreiben, dass keine Auffälligkeiten festgestellt wurden."
    )

if PHASE == 6 and st.session_state.basis_ergebnis:
    st.divider()
    st.subheader(PHASEN[6]["titel"])
    erg = st.session_state.basis_ergebnis

    st.markdown("**Initiale Gewichtungen der Leistungsdimensionen**")
    zeige_tabelle_zentriert(
        [
            {
                "Leistungsdimension": dimension,
                "Gewichtung": f"{gewicht * 100:.0f} %",
            }
            for dimension, gewicht in erg["gewichte"].items()
        ]
    )

    st.markdown("**Finale Werte der Leistungsdimensionen**")
    zeilen = []
    for dimension in erg["gewichte"]:
        zeile = {"Leistungsdimension": dimension}
        for name in alternative_namen():
            zeile[name] = erg["dim_scores"].get(name, {}).get(
                dimension,
                "Nicht relevant",
            )
        zeilen.append(zeile)
    zeige_tabelle_zentriert(zeilen)

    st.markdown("**Ranking und Empfehlung**")
    ranking = [
        {
            "Rang": erg["raenge"][name],
            "Alternative": name,
            "Gesamtpunktzahl": erg["nutzwerte"][name],
        }
        for name in sorted(erg["nutzwerte"], key=erg["nutzwerte"].get, reverse=True)
    ]
    zeige_tabelle_zentriert(ranking)
    st.info(f"Handlungsempfehlung: {erg['empfehlung']}")

    st.markdown("**Kurze Zusammenfassung**")
    zeige_aktuellen_bot_text()

    try:
        pdf_bytes = erstelle_ergebnis_pdf(
            ergebnis=erg,
            bot_text=letzter_bot_text(),
            alternativen=st.session_state.alternativen,
            baureihe=st.session_state.baureihe,
            kpis=KPIS,
            aktive_nach_alternative=aktive_kennzahlen_nach_alternative(),
            robustheit=st.session_state.robustheit,
            sensitivitaetslaeufe=st.session_state.sensitivitaetslaeufe,
        )
    except Exception as fehler:
        st.error(
            "Die Ergebnis-PDF konnte nicht erstellt werden. "
            f"Technischer Fehlertyp: {type(fehler).__name__}."
        )
    else:
        st.download_button(
            "Ergebnis-PDF herunterladen",
            data=pdf_bytes,
            file_name="entscheidungsempfehlung_produktionsnetzwerk.pdf",
            mime="application/pdf",
        )


chat_eingabe()
bewahre_scrollposition()
