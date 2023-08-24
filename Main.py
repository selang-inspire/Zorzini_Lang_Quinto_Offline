#Thermal compensation Main Python Implementation
#Author: Sebastian Lang

import pandas as pd
import numpy as np
from threading import Thread

#Parameters setting
from Machine_General import Machine

MachineName = "EVO_Quinto"                   #machine name
mode        = "Log"                   #set mode we are working with, either Sim or Compensation, or Log? TODO Log is supposed to be Online but without writing

#Data Loading       
        
Machine = Machine(MachineName, mode)
del MachineName, mode                     #deleting useless variable

#machineSpec=load_DataMachine.specs()     #acess to all machine data from Machine method















