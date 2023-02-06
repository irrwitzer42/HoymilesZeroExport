import requests, time
from requests.auth import HTTPBasicAuth
import os
import logging

ahoyIP = '192.168.10.57'
tasmotaIP = '192.168.10.90'

hoymilesInverterID = int(0) # number of inverter in Ahoy-Setup
hoymilesMaxWatt = int(1500) # maximum limit in watts (100%)
hoymilesMinWatt = int(hoymilesMaxWatt / 100 * 5) # minimum limit in watts
hoymilesMinOffsetInWatt = int(-100) # this is the target bandwidth the powermeter should be (powermeter watts should be between hoymilesMaxOffsetInWatt and hoymilesMinOffsetInWatt)
hoymilesMaxOffsetInWatt = int(-50) # this is the target bandwidth the powermeter should be (powermeter watts should be between hoymilesMaxOffsetInWatt and hoymilesMinOffsetInWatt)
hoymilesSetPointInWatt = int((hoymilesMinOffsetInWatt - hoymilesMaxOffsetInWatt) / 2 + hoymilesMaxOffsetInWatt) # this is the setpoint for powermeter watts
hoymilesMaxPowerDiff = int(hoymilesMaxWatt / 100 * 10) # maximum power difference between limit and output. used only for calculation to control faster.

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

def setLimit(hoymilesInverterID, Limit):
    url = f"http://{ahoyIP}/api/ctrl"
    data = f'''{{"id": {hoymilesInverterID}, "cmd": "limit_nonpersistent_absolute", "val": {Limit}}}'''
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    logging.info("setting new limit to %s %s",Limit," Watt")
    requests.post(url, data=data, headers=headers)

# Init
newLimitSetpoint = hoymilesMaxWatt
setLimit(hoymilesInverterID, newLimitSetpoint)
time.sleep(10)

while True:
    try:
        try:
            ParsedData = requests.get(url = f'http://{ahoyIP}/api/index').json()
            hoymilesIsReachable = bool(ParsedData["inverter"][0]["is_avail"])

            ParsedData = requests.get(url = f'http://{tasmotaIP}/cm?cmnd=status%2010').json()
            powermeterWatts = int(ParsedData["StatusSNS"]["SML"]["curr_w"])

            logging.info("HM reachable: %s",hoymilesIsReachable)
            logging.info("powermeter: %s %s",powermeterWatts, " Watt")

            if hoymilesIsReachable:
                if powermeterWatts > 0:
                    newLimitSetpoint = hoymilesMaxWatt # not enough power: increase limit to maximum
                else:
                    newLimitSetpoint = newLimitSetpoint + powermeterWatts + abs(hoymilesSetPointInWatt) # adjusting Limit to match setpoint

                # check for upper and lower limits
                if newLimitSetpoint > hoymilesMaxWatt:
                    newLimitSetpoint = hoymilesMaxWatt
                if newLimitSetpoint < hoymilesMinWatt:
                    newLimitSetpoint = hoymilesMinWatt

                # set new limit to inverter
                setLimit(hoymilesInverterID, newLimitSetpoint)
        except TypeError as e:
            logging.error(e)
            newLimitSetpoint = hoymilesMaxWatt
    finally:
        time.sleep(10)
