"""
szenarien.py
============
Beschreibungen der betrachteten Szenarien zur Konfiguration globaler
Produktionsnetzwerke. Die Beschreibungen orientieren sich an Kapitel 5.1
der Masterarbeit und werden vom Chatbot nur auf Nachfrage verwendet.
"""

SZENARIO_BESCHREIBUNGEN = {
    "Verlagerung der Produktion an anderen Standort": (
        "Bei diesem Szenario wird die Produktion eines bestehenden Produktes "
        "von einem bisherigen Produktionsstandort an einen anderen bereits "
        "bestehenden Standort innerhalb des Produktionsnetzwerks verlagert. "
        "Ein neuer Standort wird dabei nicht aufgebaut; die Standortstruktur "
        "bleibt erhalten, während sich die Zuordnung der Produkte zu den "
        "Standorten verändert. Mögliche Auslöser sind Kostenvorteile am "
        "Zielstandort, Marktnähe, Kapazitätsausgleich oder eine strategische "
        "Neuausrichtung des Produktionsnetzwerks. Das Szenario wirkt sich "
        "direkt auf den abgebenden und den aufnehmenden Standort aus und kann "
        "abhängig von der geografischen Verteilung auch Lieferantenbeziehungen "
        "beeinflussen. Eine Sonderform stellt die Teilverlagerung dar, bei der "
        "nur bestimmte Stückzahlen oder Wertschöpfungsumfänge an einen anderen "
        "Standort übergehen."
    ),
    "Eröffnung eines Produktionsstandortes": (
        "Bei diesem Szenario wird ein weiterer Produktionsstandort innerhalb "
        "des Produktionsnetzwerks eröffnet. Beweggründe können insbesondere "
        "die Nähe zu Absatzmärkten oder relevanten Lieferanten sein. Dabei kann "
        "zwischen dem Neubau einer Produktionsstätte im Sinne eines Greenfield-"
        "Projekts und dem Ausbau eines bestehenden Standortes im Sinne eines "
        "Brownfield-Projekts unterschieden werden. Insgesamt handelt es sich um "
        "eine langfristige und kapitalintensive Konfiguration mit weitreichenden "
        "Auswirkungen auf das Produktionsnetzwerk."
    ),
    "Schließung eines Produktionsstandortes": (
        "Bei diesem Szenario wird ein Produktionsstandort innerhalb des "
        "Produktionsnetzwerks geschlossen. Gründe können beispielsweise "
        "Überkapazitäten oder die Realisierung von Skalen- und Verbundeffekten "
        "sein. Die am Standort gefertigten Produkte oder Komponenten entfallen "
        "entweder ersatzlos oder werden an anderen Standorten fortgeführt. "
        "Neben den langfristigen Auswirkungen auf das Produktionsnetzwerk sind "
        "rechtliche Rahmenbedingungen sowie der mögliche Verlust "
        "standortspezifischen Unternehmenswissens zu berücksichtigen."
    ),
    "Kapazitätsanpassung eines Standortes": (
        "Bei diesem Szenario wird die Kapazität eines bestehenden Standortes "
        "erweitert oder reduziert. Es stellt eine Alternative zur Eröffnung "
        "oder Schließung eines Standortes dar und ist insbesondere bei volatilen "
        "Stückzahlen relevant, wie sie in der Klein- und Mittelserienfertigung "
        "auftreten können. Die Kapazitätsanpassung beeinflusst interne "
        "Standortstrukturen, die Auslastung, die Stückkosten sowie die "
        "Belastung der zugehörigen Lieferanten."
    ),
    "Wechsel eines Lieferanten": (
        "Bei diesem Szenario wird ein bestehender Lieferant, der für eine oder "
        "mehrere Komponenten verantwortlich ist, durch einen anderen Lieferanten "
        "ersetzt. Die Auswirkungen sind mittel- bis langfristig und betreffen "
        "vor allem den ursprünglichen sowie den neu ausgewählten Lieferanten. "
        "Relevante Entscheidungsaspekte können Versorgungssicherheit, Qualität, "
        "Kosten, Lieferzeit und die Abhängigkeit einzelner Baureihen von einem "
        "Lieferanten sein."
    ),
    "Referenzszenario": (
        "Das Referenzszenario beschreibt den aktuellen Zustand des "
        "Produktionsnetzwerks ohne Veränderung. Es dient als Vergleichsmaßstab, "
        "um die Auswirkungen anderer Szenarien gegenüber dem bestehenden Zustand "
        "bewerten zu können. Dadurch lässt sich beurteilen, ob eine "
        "Konfiguration des Produktionsnetzwerks überhaupt in Betracht gezogen "
        "werden sollte."
    ),
}
