# teleinfo-linky-with-raspberry
Surveiller sa consommation électrique en temps réel avec un compteur Linky et un Raspberry 

Adaptation pour InfluxDB 2.0

Le script verifie que l'organisation et le bucket sont existants, sinon arrêt.
Relance le service socat à chaque lancement.

Ajout de 2 services :

pitinfo_socat.service : 
lecture du flux série
Ip à adapter:

ExecStart=/usr/bin/socat -d -d pty,link=/dev/ttyUSB21,raw,ignoreeof,echo=0 tcp:192.168.xx.xxx:8888

pitinfo.service : 
lancement
A adpater:

WorkingDirectory=/home/xxxx/pitinfo
ExecStart=/usr/bin/python3 /home/xxxx/pitinfo/pitinfo-InfluxDB 2.0.py

