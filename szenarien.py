"""
szenarien.py
============
Beschreibungen der auswaehlbaren Szenario-Typen. Diese Texte werden dem
Chatbot in den System-Prompt gegeben, damit er dem Nutzer die Szenarien
erklaeren und Rueckfragen beantworten kann.

>>> HIER traegst du deine eigenen Beschreibungen ein. <<<
Die Schluessel muessen exakt den Spaltennamen der Matrix entsprechen
(verlagerung, lieferantenwechsel, sop_neu, make_or_buy, eop_restvolumen,
referenz).
"""

SZENARIO_BESCHREIBUNGEN = {
    "verlagerung": (
        "Standortverlagerung: Eine bestehende Produktion wird von einem "
        "Standort an einen anderen verlagert. [zu ergaenzen: konkrete "
        "Beschreibung, typische Ausloeser, Entscheidungsfragen]"
    ),
    "lieferantenwechsel": (
        "Lieferantenwechsel: Ein bestehender Lieferant wird durch einen "
        "anderen ersetzt. [zu ergaenzen]"
    ),
    "sop_neu": (
        "Start of Production an einem neuen Standort: Aufbau einer neuen "
        "Produktion. [zu ergaenzen]"
    ),
    "make_or_buy": (
        "Make-or-Buy: Entscheidung zwischen Eigenfertigung und Fremdbezug. "
        "[zu ergaenzen]"
    ),
    "eop_restvolumen": (
        "End of Production / Restvolumen: Auslauf einer Produktion und "
        "Behandlung des Restvolumens. [zu ergaenzen]"
    ),
    "referenz": (
        "Referenz (keine Aenderung): Das bestehende Setup ohne Eingriff, als "
        "Vergleichsmassstab. [zu ergaenzen]"
    ),
}
