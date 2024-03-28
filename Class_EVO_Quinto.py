import pandas as pd
from threading import Thread, Event
import csv
import numpy as np
from datetime import datetime
from OPC_UA_conn import OPCUAcon
from Class_Kinematic import errorMeasurement
#machine specific parameters
class EVO_Quinto:

    def __init__(self,log_file_name):
        self.MeasCycleType = "B3" #B3
        self.SensorList = ['1 B WerkstückSpanner links','2 A_axis_Drive_Structure','3 C_axis_Top_Auf_Spindelstock_Mitte','4 C_Axis_Cover','5 Touch_Probe_Holder_Spindle',
                         '6 Spindle_Structure_Front','7 B drive gap between gear', '8 B WerkstückSpanner rechts','9 B Drive gearbox','10 Oil Backflow', '11 Env Machine Front',
                         '12 Air Workingspace', '13 Env Machine back middle', '14 X drive back down', '15 Bed behind machine left, axis enclosure',
                         '16 X structure cast right', '17 Drive grinding spindle','18 Spindle back left casting','19 X Drive middle top','20 bed below front',
                         '21 Air back','22 Coolant Backflow']
        self.Kinematics = errorMeasurement(self.MeasCycleType)
        self.ErrorList = ['X0B'] #TODO Update to pivotes
        self.log_file_name = log_file_name
        #mc.FilePathTemperature = r'C:\Users\' #TODO

        self.Reference=9.5;
    def ConnectMachine(self,measurementFrequency,LogInfluxFrequency):
        self.OPC = OPCUAcon(measurementFrequency,self.log_file_name,LogInfluxFrequency)
    def OfflineFileData(self): 
        
        #loading from excel
        Temperature = pd.read_excel (self.FilePathTemperature)
        Dx = pd.read_excel (self.FilePathDx)
        Latch = pd.read_excel(self.FilePathLatch)
        
        ThermalError = ThermalErrorCalculation(Dx,Latch,self.Reference)
        Temperature, ThermalError = TableLayout(Temperature,self.SensorList, ThermalError, self.ErrorList)
        
        return ThermalError, Temperature



    def TableLayout(Temperature,SensorList, ThermalError, ErrorList):         #nice temperature dataframe layout
        SensorList = ['date','time'] + SensorList
        FirstMeas = Temperature.index.values[Temperature.iloc[:,0]==1].tolist()
        Temperature = Temperature.drop(range(0,FirstMeas[0]))
        Temperature = Temperature.drop(Temperature.columns[[0]],axis=1)
        Temperature.columns = SensorList
        
        ErrorList = ['time'] + ErrorList
        ThermalError.columns = ErrorList

        return Temperature, ThermalError



    def ThermalErrorCalculation(Dx,Latch,Reference):  #error calculation
        ThermalError = pd.DataFrame()
        
        #set time of thermal error as the last measurement taken (latch)
        ThermalError.insert(0,"time",Latch.iloc[1:,0])
        
        #calculation of thermal error
        ThermalError.insert(1,"error",-Dx.iloc[1:,1]-Reference+Latch.iloc[1:,1]) 
        ThermalError.iloc[:,1] = (ThermalError.iloc[0:,1] - ThermalError.iloc[0,1])*1000
            
        return ThermalError


#online compensation functions



