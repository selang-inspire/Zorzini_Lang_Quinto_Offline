#Thermal compensation Main Python Implementation
#Author: Sebastian Lang

import pandas as pd
import numpy as np

#IMPORTANT: Currently The HMI has to be run as admin to allow the Compensation file sharing to work!

#Parameters setting
from Machine_General import MT

MachineName = "EVO_Quinto"                   #machine name
mode        = "Log"                   #set mode we are working with, either Sim or Compensation, or Log? TODO Log is supposed to be Online but without writing
measurementFrequency=5 #Measurement frequency in seconds for drives and other recorded values
log_file_name = "D:\\MainThermokompensation\\Messdaten\\Log_AP_21_03_2024.csv"
LogInfluxFrequency=10 #TODO Log only at logfrequency, measure and aggregate average/filter? at measurementFrequency currently not implemented
# TODO? Move all to settings variable

#Data Loading
        
MT = MT(MachineName, mode,measurementFrequency,log_file_name,LogInfluxFrequency)
del MachineName, mode                     #deleting useless variable

#machineSpec=load_DataMachine.specs()     #acess to all machine data from Machine method


print("Done")









