import pandas as pd
from threading import Thread, Event
import csv
import numpy as np
from datetime import datetime

#machine specific parameters
class specs:

    def __init__(mc):
        mc.SensorList = ['1 B WerkstückSpanner links','2 A_axis_Drive_Structure','3 C_axis_Top_Auf_Spindelstock_Mitte','4 C_Axis_Cover','5 Touch_Probe_Holder_Spindle','6 Spindle_Structure_Front','7 B drive gap between gear', ...
                         '8 B WerkstückSpanner rechts','9 B Drive gearbox','10 Oil Backflow', '11 Env Machine Front','12 Air Workingspace', '13 Env Machine back middle', '14 X drive back down', '15 Bed behind machine left, axis enclosure',...
                         '16 X structure cast right', '17 Drive grinding spindle','18 Spindle back left casting','19 X Drive middle top','20 bed below front','21 Air back','22 Coolant Backflow']
        mc.ErrorList = ['X0B'] #TODO Update to pivotes  
        mc.FilePathTemperature = r'C:\Users\'

        mc.Reference=9.5;
   
def OfflineFileData(machineSpec): 
    
    #loading from excel
    Temperature = pd.read_excel (machineSpec.FilePathTemperature)
    Dx = pd.read_excel (machineSpec.FilePathDx)
    Latch = pd.read_excel(machineSpec.FilePathLatch)
      
    ThermalError = ThermalErrorCalculation(Dx,Latch,machineSpec.Reference)
    Temperature, ThermalError = TableLayout(Temperature,machineSpec.SensorList, ThermalError, machineSpec.ErrorList)
    
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
class OnlineTempData (Thread):
    
    def __init__(mc, machineSpec):
        Thread.__init__(mc)
        print('temp')
        mc.Data = []  #empty vector to be filled with temperature data
        mc.machineSpec=machineSpec 
  	
    def run(mc):
        print ("Starting T")
        
        #example of reading a single data from cvs JUST FOR TESTING
        mc.Data = pd.read_csv(r"C:\Users\sofit\Desktop\eth\Bachelor Thesis\BT folder\Measurements\Evo 100\Daten Messung 1 Evo 100\Temperaturverlauf1.csv", 
                              sep=';',header=None, names=['Number', 'Date',	'Time'] + mc.machineSpec.SensorList, 
                              usecols=mc.machineSpec.SensorList,
                              nrows=1, skiprows=23)
        print(mc.Data.info())
        
        #writing data on a new cvs file
        with open('Online_data.csv', 'w') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            filewriter.writerow(['Time'] + mc.machineSpec.SensorList)
            now = datetime.now()
            t = str(mc.Data)
            mc.Data = now.strftime() + str(mc.Data)
            filewriter.writerow(mc.Data)
        
        print ("Ending T")
        
        
class OnlineMachineData(Thread):
    
    def __init__(mc, machineSpec):
        Thread.__init__(mc)
        print('err')
        mc.Data = []                       #empty vector to be filled with temperature data
  	       
    def run(mc):
        print ("Starting E")
        mc.Data = 0
        print ("Ending E")
        



