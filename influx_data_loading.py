"""
Created on Tue Nov 8 11:32:26 2022
@author: sofit
"""

#first try Influxdb
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

#please remember to update token and ip address - set up
token="MggjMzZMpNVVqS2Eg4RuTA_aFMLkyZ_THQHqaOFsr5FsX6hQhkTkVsh1DIEN0Tl64J_jPApVqFs0Puuqu7JYGQ=="
url = "http://localhost:8086"
org = 'st'

#creating the database - bucket is the database
client = influxdb_client.InfluxDBClient(url=url,token=token,org=org)
bucket="py trial watchdog"

#generating point to be stored 

point = (
    Point("hey")
    .tag("tagname1", "tagvalue1")
    .field("field1",3)
)
#writing the data into the database
write_api = client.write_api(write_options=SYNCHRONOUS)
write_api.write(bucket=bucket, org="st", record=point)

time.sleep(1) # separate points by 1 second