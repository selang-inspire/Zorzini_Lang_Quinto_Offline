#Thermal compensation
#Starting date: October 2022
#Author: Sofia Talleri

import pandas as pd
import numpy as np
from threading import Thread

#Parameters setting
from Machine_General import Machine

MachineName = "EVO_Quinto"                   #machine name
mode        = "Sim"                   #set mode we are working with, either Sim or Online

#Data Loading       
        
Machine = Machine(MachineName, mode)
del MachineName, mode                     #deleting useless variable

#machineSpec=load_DataMachine.specs()     #acess to all machine data from Machine method















