"""
Created on Tue Nov 8 11:32:26 2022
@author: sofit
"""

#first try Influxdb
"""
Created on Tue Nov 8 11:32:26 2022

@author: Sebastian Lang, sofit
"""
import influxdb_client, os, time
import numpy as np
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

def influx_export(value,ServerInflux,DictionaryNames,timezone):

  try:
    #please remember to update token and ip address - set up for data exchange
    if ServerInflux=="Local":
      token = "pdOv_D18k83fgabojWqedk0MiXr_gClsw5oqBBCZbqlbXvkzi85Y9Aq0PSmRkYK8rmDSTBnvGG7k27-5m4j0Fg=="
      url = "http://192.168.1.101:8086"
      org = 'QuintoCompLocal'
    elif ServerInflux=="WS16":
      token = "4MecLF8nQznwGWhGSPQhi6v_Y3dvyoHVqlUvF7JZqEDIZGWqvwdwQQBvZ-oEObwkpCjj4oHb8_uTFm8VmDSYvQ=="
      #url = "http://10.144.34.102:8086"
      url = "http://isim-ws016.intern.ethz.ch:8086"

      org = 'ThermoComp'

    if value is None:#Todo Switch between Temp and ThermalError
      raise Exception('value is None')
    #prepare data
    flattened_value = np.concatenate([item.flatten() if isinstance(item, np.ndarray) else item for item in value])
    if not len(flattened_value)-1==len(DictionaryNames): #Minus 1 because the first value is the time
      raise Exception('value and DictionaryNames have to be of same length')

    #creating the client object
    client = influxdb_client.InfluxDBClient(url=url,token=token,org=org)
    bucket="Quinto164"

    #writing the data into the database
    write_api = client.write_api(write_options=SYNCHRONOUS)


    for i in range(len(DictionaryNames)):
      point = (
        Point(DictionaryNames[i])
        .field("temperature",flattened_value[i+1].astype(float))#value[i+1] because the first value is the time
        .time(timezone.localize(datetime.strptime(flattened_value[0],"%d.%m.%Y %H:%M:%S.%f")))
      )
      write_api.write(bucket, org, point)
  except:
    raise Exception('error arised while exporting to influx')
