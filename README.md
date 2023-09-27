# BachelorProjekt

Peer to Peer File Sharing mit Netzwerkodierung auf basis von Elgamal Verschlüsselung

# Peer to Peer:
    Es wird als erstes ein Server Node gestartet. Jede weitere Instanz verbindet sich zunächst mit dem 
    Server node und fragt nach einem zufälligen Node aus dem Netzwerk.
    Der Server Node speichert alle Vorhandenen Nodes.
    Der neue Node verbindet sich dann mit dem zufälligen Node des Servers.
    Alle Nodes laufen momentan noch über 127.0.0.1 und einem unterschiedlichen Port.

    Eventuell erweitern auf IP adresse und testen auf unterscchiedlichen rechnern innerhalb eines Netzwerks (?)

# File Sharing:
    Jeder Node kann eine File auswählen, welche er über das Netzwerk an alle anderen Versenden möchte.
    Die Datei wird in einzelne (gleichgroße) Packete unterteilt und diese in einer Liste zwischengespeichert.
    Danach werden die einzelnen Packete mit der Elgamal Verschlüsselung verschlüsselt und der Schlüssel für jedes Packet wird in einer weiteren Liste 
    zwischengespeichert.
    
    Combinationen werden erstellt, indem die einzelnen Packete mit jeweils zufälligen
    Zahlen exponentiert und miteinander multipliziert werden.

        (c1,c2)^a * (c1,c2)^b * ....

    Jede einzelne combination wird mit den exponenten versendet. Sobal ein Node genügend
    combinationen und exponenten hat, kann dieser die Zahlen entschlüsseln und die 
    Datei wider herstellen.

    Hierzu werden die empfangen Kombinationen durch ElGamal Entschlüsselt (x1,x2,..,xn), und diese mit der modularen inversen matrix der Exponenten multipliziert und exponentiert.

        B = A^-1 % q          m1 = x1**B[0][0] * x2**B[0][1] * ... * xn**B[0][n]
                              m2 = x1**B[1][0] * x2**B[1][1] * ... * xn**B[1][n]
                                        .....         .....           .....
                              mn = x1**B[n][0] * x2**B[n][1] * ... * xn**B[n][n]

    Hierdurch werden die Uhrsprünglichen Nachrichten wieder berechnet und wir byte Werte 
    davon werden wieder in eine neue Datei geschrieben.


# Netzwerkodierung:
    Ein Node sammelt und versendet solange Nachrichten, bis dieser genug kombinationen,
    sowie eine ausreichende Matrix der Exponenten hat. 
    Nur nodes wie diese sind in der Lage die entschlüsselten Nachrichten wieder zu berechnen.

# Installation
    Clone das Repository:
        git clone ...

    Öffne eine Kommandozeile und starte das Programm mittels dem Befehl:
        python3 app_2.py

    Starte in weiteren Kommandozeilen beliebig viele Nodes mit dem gleichen Befehl.
    Diese Verbinden sich automatisch mit dem Netzwerk.

# Probleme
    > Wenn das GUI window geschlossen wird, läuft das Programm im Hintergrund noch weiter
    > Wenn ein Node das Netzwerk verlässt, bekommen es noch nicht alle mit (Der Server Node auch nicht)
    > Wenn der Server Node das Netzwerk verlässt, gibt es keinen neuen Server Node mit den aktuellen Nodes
    > Nur eine Datei herunterladen, wenn diese auch vollständig ist