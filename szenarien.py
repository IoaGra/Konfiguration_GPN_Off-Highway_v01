"""
szenarien.py
============
Beschreibungen der auswaehlbaren Szenario-Typen. Diese Texte werden dem
Chatbot in den System-Prompt gegeben und dem Nutzer angezeigt, damit er die
Szenarien versteht.

>>> HIER traegst du deine eigenen Beschreibungen ein. <<<
Die Schluessel (verlagerung, ...) muessen exakt den Spaltennamen der Matrix
entsprechen. Anzeigetexte duerfen Umlaute enthalten.
"""

SZENARIO_BESCHREIBUNGEN = {
    "verlagerung": (
        "Standortverlagerung: Eine bestehende Produktion wird von einem "
        "Standort an einen anderen verlagert. [zu ergänzen: konkrete "
        "Beschreibung, typische Auslöser, Entscheidungsfragen]"
    ),
    "lieferantenwechsel": (
        "Lieferantenwechsel: Ein bestehender Lieferant wird durch einen "
        "anderen ersetzt. [zu ergänzen]"
    ),
    "sop_neu": (
        "Start of Production an einem neuen Standort: Aufbau einer neuen "
        "Produktion. [zu ergänzen]"
    ),
    "make_or_buy": (
        "Make-or-Buy: Entscheidung zwischen Eigenfertigung und Fremdbezug. "
        "[zu ergänzen]"
    ),
    "eop_restvolumen": (
        "End of Production / Restvolumen: Auslauf einer Produktion und "
        "Behandlung des Restvolumens. [zu ergänzen]"
    ),
    "referenz": (
        "Referenz (keine Änderung): Das bestehende Setup ohne Eingriff, als "
        "Vergleichsmaßstab. [zu ergänzen]"
    ),
}
