"""
szenarien.py (V6)
Beschreibungen der Szenario-Typen (Quelle: szenarien.txt).
Schluessel = Spaltennamen der Szenario-Kennzahl-Matrix.
"""

SZENARIO_BESCHREIBUNGEN = {
    "Standortverlagerung": (
        "Bei einer Standortverlagerung wird die Produktion eines bestehenden "
        "Produktes von seinem aktuellen Standort an einen anderen verlagert. "
        "Typische Auslöser sind steigende Kosten am bisherigen Standort, Nähe zu "
        "wichtigen Absatzmärkten oder Kunden, geopolitische Risiken, "
        "Kapazitätsengpässe oder eine konzernweite Neuausrichtung des "
        "Produktionsnetzwerks. Die Entscheidungsfrage lautet meist: An welchen "
        "Standort sollte verlagert werden – oder lohnt sich die Verlagerung "
        "überhaupt? Verglichen werden dabei die infrage kommenden Zielstandorte "
        "untereinander sowie gegen das Referenzszenario (Verbleib am aktuellen "
        "Standort), sodass sichtbar wird, welchen Unterschied eine Verlagerung "
        "tatsächlich bewirken würde. "
    ),
    "Lieferantenwechsel": (
        "Beim Lieferantenwechsel wird ein bestehender Lieferant durch einen "
        "anderen ersetzt. Anlass kann der Wegfall eines Lieferanten sein (etwa "
        "durch Insolvenz, Qualitätsprobleme oder geopolitische Spannungen) oder "
        "das aktive Streben nach besseren Konditionen, höherer "
        "Versorgungssicherheit oder kürzeren Lieferwegen. Die Entscheidungsfrage "
        "lautet: Welcher alternative Lieferant ist die beste Wahl – oder sollte "
        "der bestehende beibehalten werden? Verglichen werden die "
        "Lieferantenalternativen untereinander und gegen das Referenzszenario "
        "(Beibehaltung des aktuellen Lieferanten). Gerade wenn der Wechsel unter "
        "Zeitdruck erfolgt, ist auch das Vertrauen in die zugrunde liegenden "
        "Daten ein wichtiger Hinweis. "
    ),
    "Start of Production (neuer Standort)": (
        "Beim Start of Production an einem neuen Standort geht es um den Aufbau "
        "einer Produktion für ein Produkt, das bisher an keinem Standort "
        "gefertigt wird. Anlass ist typischerweise die Einführung eines neuen "
        "Produktes oder die Erweiterung des Produktionsnetzwerks. Die "
        "Entscheidungsfrage lautet: An welchem der möglichen Standorte sollte die "
        "Produktion anlaufen? Hier werden die infrage kommenden Standorte direkt "
        "miteinander verglichen. Anders als bei einer Verlagerung gibt es keinen "
        "bestehenden Zustand, der als „keine Änderung\" dienen könnte – der "
        "Vergleich findet daher ausschließlich zwischen den Standortoptionen "
        "statt. "
    ),
    "Make-or-Buy": (
        "Bei einer Make-or-Buy-Entscheidung wird abgewogen, ob eine Komponente "
        "oder ein Produkt selbst gefertigt (Make) oder von einem externen "
        "Anbieter bezogen werden soll (Buy). Auslöser sind etwa "
        "Kostenüberlegungen, freie oder fehlende eigene Kapazitäten, Fragen des "
        "Know-how-Schutzes oder die gewünschte Flexibilität. Die "
        "Entscheidungsfrage lautet: Eigenfertigung oder Fremdbezug – und falls "
        "Fremdbezug, über welchen Anbieter? Verglichen werden die Option der "
        "Eigenfertigung und die Bezugsalternativen, je nach Ausgangslage auch "
        "gegen das Referenzszenario (Beibehaltung der bisherigen Bezugs- oder "
        "Fertigungsweise). "
    ),
    "End of Production / Restvolumen": (
        "Beim End of Production läuft die Produktion eines Produktes aus. Im "
        "Mittelpunkt steht die Frage, wie das verbleibende Restvolumen bis zum "
        "endgültigen Auslauf behandelt wird – etwa weiterhin am bisherigen "
        "Standort, durch Verlagerung an einen Standort mit freien Kapazitäten "
        "oder über einen externen Bezug. Auslöser sind das Ende des "
        "Produktlebenszyklus, Nachfolgeprodukte oder die Freigabe von "
        "Kapazitäten. Die Entscheidungsfrage lautet: Wie wird das Restvolumen am "
        "sinnvollsten produziert? Verglichen werden die möglichen "
        "Auslaufstrategien untereinander und gegen das Referenzszenario "
        "(unveränderte Weiterproduktion). "
    ),
    "Referenz (keine Änderung)": (
        "Das Referenzszenario beschreibt das bestehende Setup ohne jeden Eingriff "
        "– also den aktuellen Zustand, wenn keine Entscheidung getroffen und "
        "nichts verändert wird. Es ist selbst keine eigenständige "
        "Handlungsoption, sondern dient als Vergleichsmaßstab: Erst der Vergleich "
        "gegen „keine Änderung\" macht sichtbar, ob und in welchem Umfang eine "
        "betrachtete Alternative tatsächlich eine Verbesserung bringt. In manchen "
        "Fällen – etwa beim Aufbau einer völlig neuen Produktion – gibt es keinen "
        "bestehenden Zustand, gegen den verglichen werden könnte; dann entfällt "
        "das Referenzszenario, und die Alternativen werden direkt gegeneinander "
        "bewertet. "
    ),
}
