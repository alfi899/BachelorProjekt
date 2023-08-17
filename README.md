# BachelorProjekt

Peer to Peer File Sharing mit Netzwerkodierung auf basis von Elgamal Verschlüsselung

# Peer to Peer:
    Es wird als erstes ein Server Node gestartet. Jede weitere Instaz verbindet sich zunächst mit dem 
    Server node und fragt nach einem zufälligen Node aus dem Netzwerk.
    Der Server Node speichert alle Vorhandenen Nodes.
    Der neue Node verbindet sich dann mit dem zufälligen Node des Servers.
    Alle Nodes laufen momentan noch über 127.0.0.1 und einen unterscchiedlichen Port.

    Eventuell erweitern auf IP adresse und testen auf unterscchiedlichen rechnern innerhalb eines Netzwerks (?)

# File Sharing:
    Jeder Node kann eine File auswählen, welche er über das Netzwerk an alle anderen Versenden möchte.
    Die Datei wird in einzelne (gleichgroße) Packete unterteilt und diese in einer Liste zwischengespeichert.
    Danach werden die einzelnen Packete mit der Elgamal Verschlüsselung verschlüsselt und der Schlüssel für jedes Packet wird in einer weiteren Liste 
    zwischengespeichert.
    Danach wird eine zufällige Matrix generiert (Momentan über GF(5)), diese Matrix hat die größe wie ein einzelnens Packet (size x size)
    Nun wird jedes packet mit der Matrix multipliziert um das Kodierte Packet zu erlangen.
    Dann wird jedes Packet einzeln an alle Nachbar Nodes versendet in dem Format:

        {'PACKET': packet nummer, 'GESMAT': gesamt anzahl der packete, 'FORMAT': Dateiformat der zuversendeten Datei, 'Matrix': zufallsmatri
        'encoded_packet': Das Kodierte Packet, 'public_key': Elgamal public_key}

    Wird eine solche Nachricht empfangen, wird diese in einer Liste zwischengespeichert, mit allen anderen Nachtichten.
    Danach wird über diese Liste iteriert und jedes Element wird folgenden Schritten unterzogen:
        1. Die Nachricht wird aufgeteilt in ihre einzelteile (PACKET, encoded_packet, public_key,...)
        2. Das Packet (encoded_packet) wird mittels inverser Matrixmultiplication dekodiert
        3. Das dekodierte Packet wird mittels Elgamal decryption und dem public_key wieder in das Uhrsprungspacket verwandelt
        4. Alle 

    (Was wenn ein Node das Netzwerk verlässt ??)


# Netzwerkodierung:
    Die Datei wird in Packeten mit der Matrix versendet. Dadurch können Sie wieder hergestellt werden.
    Jeder Node, der ein Packet empfängt, sendet es automatisch an alle seine Nachbarn weiter.

    Theoretisch müsste hier eine lineare Kombination der Packete versendet werden, wenn zwei Packete von verschiedenen 
    Nodes empfangen werden (?)