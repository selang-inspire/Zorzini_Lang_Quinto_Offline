#Thermal compensation Main Python Implementation
#Author: Sebastian Lang

import pandas as pd
import numpy as np
from threading import Thread


#Parameters setting
from Machine_General import MT

MachineName = "EVO_Quinto"                   #machine name
mode        = "Log"                   #set mode we are working with, either Sim or Compensation, or Log? TODO Log is supposed to be Online but without writing
measurementFrequency=1 #Measurement frequency in seconds for drives and other recorded values
Logfrequency=30 #TODO Log only at logfrequency, measure and aggregate average/filter? at measurementFrequency currently not implemented
# TODO? Move all to settings variable

#Data Loading
        
MT = MT(MachineName, mode,measurementFrequency)
del MachineName, mode                     #deleting useless variable

#machineSpec=load_DataMachine.specs()     #acess to all machine data from Machine method





print("Done")









