#Thermal compensation Main Python Implementation
#Author: Sebastian Lang

import pandas as pd
import numpy as np
from threading import Thread

#IMPORTANT: Currently The HMI has to be run as admin to allow the Compensation file sharing to work!

#Parameters setting
from Machine_General import MT

MachineName = "EVO_Quinto"                   #machine name
mode        = "Sim"                   #set mode we are working with, either Sim or Compensation, or Log? TODO Log is supposed to be Online but without writing
measurementFrequency=1 #Measurement frequency in seconds for drives and other recorded values
log_file_name = "C:\\Users\\Admin.AGATHON-7OEU3S8\\Desktop\\MainThermokompensation\\Messdaten\\Log_AP_26_10_2023.csv"
Logfrequency=30 #TODO Log only at logfrequency, measure and aggregate average/filter? at measurementFrequency currently not implemented
# TODO? Move all to settings variable

#Data Loading
        
MT = MT(MachineName, mode,measurementFrequency,log_file_name)
del MachineName, mode                     #deleting useless variable

#machineSpec=load_DataMachine.specs()     #acess to all machine data from Machine method


print("Done")









