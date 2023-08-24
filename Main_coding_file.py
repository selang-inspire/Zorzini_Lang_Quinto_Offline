#Thermal compensation
#Starting date: October 2022
#Author: Sofia Talleri

import pandas as pd
import numpy as np
from threading import Thread

#Parameters setting
import EVO_Quinto as load_DataMachine        #change name of imported module according to machine

MachineName = "EVO_Quinto"                   #machine name
mode        = "Sim"                   #set mode we are working with, either Sim or Online
machineSpec=load_DataMachine.specs()     #acess to all machine data from Machine method

#Data Loading
class Machine:
    
    def __init__(mc, Name, mode):
        if mode == "Sim":
            mc.MachineName  = Name
            mc.Mode         = mode
            mc.ThermalError = ()
            mc.Temperature  = ()
            mc.LoadDataOffline()
            
        else :
            mc.MachineName  = Name
            mc.Mode         = mode
            mc.ThermalError = ()
            mc.Temperature  = ()
            mc.LoadDataOnline()
    
    def LoadDataOffline(mc):
        ThermalError, Temperature = load_DataMachine.OfflineFileData(machineSpec)
        mc.ThermalError = ThermalError
        mc.Temperature  = Temperature
            
    def LoadDataOnline(mc):
        OnlineCompT = load_DataMachine.OnlineTempData(machineSpec) #creating threads
        OnlineCompT.start()  #starting threads
        OnlineCompE = load_DataMachine.OnlineErrData(machineSpec)
        OnlineCompE.start()
        OnlineCompT.join()
        OnlineCompE.join()                #wait for the all thread to be over in order to continue witht the code
        
        mc.ThermalError = OnlineCompE.Data
        mc.Temperature  = OnlineCompT.Data
        
        
Machine = Machine(MachineName, mode)
del MachineName, mode                     #deleting useless variable














