#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# __author__ = "Sébastien Reuiller"
# __licence__ = "Apache License 2.0"

# # Version pour influxdb 2.0 
# pip3 install influxdb-client pySerial

# A adapter :
# url="http://localhost:8086" 
# Doivent déjà être créés via influxdb / data 
# orga = 
# bucket = 
# token = 


# Exemple de trame:
# {
#  'OPTARIF': 'HC..',        # option tarifaire
#  'IMAX': '007',            # intensité max
#  'HCHC': '040177099',      # index heure creuse en Wh
#  'IINST': '005',           # Intensité instantanée en A
#  'PAPP': '01289',          # puissance Apparente, en VA
#  'MOTDETAT': '000000',     # Mot d'état du compteur
#  'HHPHC': 'A',             # Horaire Heures Pleines Heures Creuses
#  'ISOUSC': '45',           # Intensité souscrite en A
#  'ADCO': '000000000000',   # Adresse du compteur
#  'HCHP': '035972694',      # index heure pleine en Wh
#  'PTEC': 'HP..'            # Période tarifaire en cours
# }

import serial
import logging
import time
import requests
import influxdb_client
import sys

from datetime import datetime

from influxdb_client import InfluxDBClient
from influxdb_client import BucketsService, Bucket, PostBucketRequest

# création du logguer / Chemin à adapter 
logging.basicConfig(filename='/var/log/pitinfo/releve.log', level=logging.INFO, format='%(asctime)s %(message)s')
logging.info("Lancement pitinfo..")

# A adapter
url="http://localhost:8086"
orga = "one"
bucket = "test"
token = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
serveur = "serveur"
capteur = "pitinfo"

#establish a connection
client = influxdb_client.InfluxDBClient(
  url=url,
  token=token,
  org=orga
)
influxdb_buckets_api = client.buckets_api()
influxdb_org_api = influxdb_client.OrganizationsApi(client)

#Get all organizations / verification orga existe
orgs = influxdb_org_api.find_organizations()
#Get organization id
for org in orgs:
    if org.name == orga:
        logging.info('Organisation ' + orga +' OK')
    else :
        logging.info("Organisation inconnue:" + orga)
        print("Organisation inconnue: " + orga)
        logging.info("ARRET")
        sys.exit()

#Get all buckets in current org / vérification bucket existe
bucket_objects = influxdb_buckets_api.find_buckets()

connected = False
for x in range ( len(bucket_objects._buckets)) :
    if bucket in bucket_objects._buckets[x].name:
        logging.info('Bucket Ok :'+ bucket)
        connected = True
        break

if connected == False :
    logging.warning('Bucket inconnu :' +bucket)
    print("Bucket inconnu: " + bucket)
    logging.warning("ARRET")
    sys.exit()

#instantiate the WriteAPI 
write_api = client.write_api()

# clés téléinfo
# int_measure_keys = ['IMAX', 'HCHC', 'IINST', 'PAPP', 'ISOUSC', 'ADCO', 'HCHP']
# avant int_measure_keys = ['ADCO', 'ISOUSC', 'BASE', 'IINST', 'ADPS', 'IMAX', 'PAPP']
#int_measure_keys = ['ADCO', 'OPTARIF', 'ISOUSC', 'BASE', 'PTEC', 'IINST', 'IMAX', 'PAPP', 'HHPHC']
int_measure_keys = ['ADCO', 'ISOUSC', 'BASE', 'HCHC', 'HCHP', 'ADPS', 'IINST', 'IMAX', 'PAPP']
txt_measure_keys = ['OPTARIF', 'PTEC', 'MOTDETAT']

def add_measures(measures, time_measure):
    points = []

    for measure, value in measures.items():
        point = {
                    "measurement": measure,
                    "tags": {
                        "serveur": serveur,
                        "capteur": capteur,
                    },
                    "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "fields": {
                        "value": value
                    }
                }
        #print(point)            
        points.append(point)

        write_api.write(bucket=bucket,org=orga,record=points)


def main():

    # restart socat
    import os
    os.system("sudo systemctl restart pitinfo_socat.service")
    logging.info('Restart socat')
    time.sleep (5)

    with serial.Serial(port='/dev/ttyUSB21', baudrate=1200, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                       bytesize=serial.SEVENBITS, timeout=1) as ser:

        logging.info("Info lue sur pitinfo sur /dev/ttyUSB21..")

        trame = dict()

        # boucle pour partir sur un début de trame
        line = ser.readline()
        while b'\x02' not in line:  # recherche du caractère de début de trame
            line = ser.readline()

        # lecture de la première ligne de la première trame
        line = ser.readline()

        while True:
            line_str = line.decode("utf-8")
            #print(line_str)
            ar = line_str.split(" ")
            #print (ar)
            try:
                key = ar[0]
                if key in int_measure_keys :
                    value = int(ar[1])
                    trame[key] = value
                elif key in txt_measure_keys :
                    value = ar[1]
                    trame[key] = value
                
                    checksum = ar[2]
                
                    if b'\x03' in line:  # si caractère de fin dans la ligne, on insère la trame dans influx
                        del trame['ADCO']  # adresse du compteur : confidentiel!
                                            
                        time_measure = time.time()
                        # print(ar[0])
                        
                        # permet de n'avoir que les bonnes trames
                        if ar[0] == "MOTDETAT" :
                        
                            # insertion dans influxdb
                            
                            add_measures(trame, time_measure)
                            # print(trame)
                                
                            # ajout timestamp pour debugger
                            trame["timestamp"] = int(time_measure)
                            logging.debug(trame)

                            trame = dict()  # on repart sur une nouvelle trame

            except Exception as e:
                logging.error("Exception : %s" % e)
            line = ser.readline()


if __name__ == '__main__':
    if connected:
        main()
