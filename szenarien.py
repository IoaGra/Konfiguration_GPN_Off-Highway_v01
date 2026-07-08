"""
szenarien.py (V8)
Beschreibungen der sechs Szenarien nach Abbildung 5.1 der Masterarbeit.
Schluessel = Spaltennamen der Szenario-Kennzahl-Matrix.
Schliessung/Kapazitaetsanpassung: neu formuliert, zu pruefen.
"""

SZENARIO_BESCHREIBUNGEN = {
    "Verlagerung der Produktion an anderen Standort": (
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
    "Eröffnung eines Produktionsstandortes": (
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
    "Schließung eines Produktionsstandortes": (
        "Bei der Schließung eines Produktionsstandortes entfällt ein Standort aus "
        "dem Produktionsnetzwerk – typische Auslöser sind Überkapazitäten oder "
        "angestrebte Skaleneffekte. Die dort gefertigte Produktion entfällt "
        "entweder ersatzlos oder wird an andere Standorte verlagert. Die "
        "Entscheidungsfrage lautet: Welcher Standort sollte geschlossen werden "
        "und wie wird die betroffene Produktion behandelt? Verglichen werden die "
        "Schließungsalternativen untereinander und gegen das Referenzszenario "
        "(Weiterbetrieb). [Formulierung zu prüfen] "
    ),
    "Kapazitätsanpassung eines Standortes": (
        "Bei der Kapazitätsanpassung wird die Kapazität eines Standortes "
        "erweitert oder reduziert – typisch bei volatilen Stückzahlen. Die "
        "Entscheidungsfrage lautet: An welchem Standort und in welchem Umfang "
        "sollte die Kapazität angepasst werden? Verglichen werden die "
        "Anpassungsalternativen untereinander und gegen das Referenzszenario "
        "(unveränderte Kapazität). [Formulierung zu prüfen] "
    ),
    "Wechsel eines Lieferanten": (
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
    "Referenzszenario": (
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
