'''
Thermal compensation Main Python Implementation
Author: Sebastian Lang, Mario Zorzini

##################Description##################
- This Software is used to compensate the thermal error of a machine tool
- It provides an interface to the user to load the data, train the model and compensate the thermal error
- The Software is build up in two environments:
    --> Offline: The user can train the model, set a training range and simulate the whole implementation of the compensation with already provided data
    --> Online: The user can now make an active real time prediction & correction of the TCP of the machine tool
- The Software is build up in a modular way, so that the user can easily add new models, features, sensors, etc.
- Furthermore, it can be easily adapted to other machine tools, as the data loading is done in a general way
- The general data structure is a dictionary, where the keys are the names of the sensors and the values are the corresponding dataframes (pandas)
    --> The dataframes have a 'Time' column and the corresponding Features values
    --> Important: The 'Time' column must be named 'Time', NOT 'time' or 'TIME'
    --> 'Time' column must be in datetime format (e.g. 2024-05-08 14:46:31.073)
    --> Thermal Error data structure: Each key in a dictionary consists of a pandas dataframe with columns: 'Time', 'Wert_1', 'Wert_4'
    --> 'Wert_1': name of the thermal error (e.g. X0B, Y0B, Z0B, A0B, B0B, C0B)
    --> 'Wert_4': the actual value of the thermal error
################################################
- For Questions or Feedback please contact: mzorzini@ethz.ch
'''


import pandas as pd
import numpy as np

#IMPORTANT: Currently The HMI has to be run as admin to allow the Compensation file sharing to work!

#Parameters setting
from Machine_General import MT
import matplotlib
#from subprocess import Popen
#import sys
matplotlib.use('TkAgg') #used for the plot to be shown in a window

# -------------------------------------------------------------------------------------------------------------------------------------------------------
# Machine Parameters
MachineName = "EVO_Quinto"            #machine name
mode        = "Compensation"          #set mode we are working with, either Sim or Compensation, or Log? TODO Log is supposed to be Online but without writing
Compensation_Steps = 2000 #Number of Compensation Steps (multiple of measurement Frequency)
ModelFrequency=10 #Model (not measurement) frequency in seconds for read-in new data in active compensation (ONLINE)
log_file_name =  "C:\\Users\\Admin.AGATHON-7OEU3S8\\Desktop\\MainThermokompensation\\Messdaten\\Log_AP_22_02_2024.csv"
Logfrequency=1 #TODO Log only at logfrequency, measure and aggregate average/filter? at measurementFrequency currently not implemented
model_directory = "C:\\Users\\mzorzini\\OneDrive - ETH Zurich\\Zorzini_Inspire\\Semester_Project\\03_Python_Scripts\\Models_Storage"
Comp_Model = 'ARX' #None, "ARX", "FFNN", "LSTM" define which Model to use for compensation
Input_Selection_Model = None #None, 'LASSO', 'Group LASSO'

# -------------------------------------------------------------------------------------------------------------------------------------------------------
# Feature Set Selection
TemperatureSensors = True #True: Only Temperature Sensors will be used
Engineering_Know_SensorSet = False #True: Only Engineering Know Sensor Set will be used
Eval_SensorSet_Paper = True #True: Only FE optimized Sensor Set from Paper will be used (FE optimized sensor set)
Env_TempSensors = False #True: Only Environmental Temperature Sensors will be used

cheap_Features = False #True: Only processed cheap Features will be used
EnergyToPower = False #True: Processed Energy will be converted to Power & used as Feature
EnergyToPower_NonSmoothedEnergy = False #True: processed without MA, Energy will be converted to Power without smoothing & used as Feature
indigTemp = False #True: Processed Indigenous Temperature will be used & used as Feature
Raw_indigTemp = False #True: Raw Measurement Indigeneous Temperature Data will be used & used as Feature
Raw_PowerData = False #True: Raw Measurement Power Data will be used & used as Feature
# -------------------------------------------------------------------------------------------------------------------------------------------------------
# Train Data in [%] (only for Simulation (OFFLINE)
train_len = 0.56 #0.35 #0.8 (Only for OFFLINE, in ONLINE resp. Compensation Mode the Train Data is defined by the amount of data you load in)

######Excel Error File & Time Settings######
start_time = "04/16/2024 02:40:00.00 PM" #"04/16/2024 01:40:00.00 PM" #"04/10/2024 05:00:00.00 PM"#"04/10/2024 05:00:00.00 PM"#"04/16/2024 03:00:00.00 PM" #"04/10/2024 05:00:00.00 PM" #"04/10/2024 05:00:00.00 PM" #"04/16/2024 03:00:00.00 PM" #"04/15/2024 02:00:00.00 PM" #"03/18/2024 04:10:00.00 PM" #This is the Time when the Imported Measurement Dataframe data should start to bea read in--> e.g. Training Dataframe for ONLINE, or whole Dataset for OFFLINE
end_time = "04/27/2024 10:30:00.00 PM" #"04/26/2024 10:30:00.00 PM"#"04/17/2024 05:50:00.00 PM" #"04/17/2024 05:50:00.00 PM"  #"04/17/2024 10:00:00.00 AM" #"04/17/2024 03:45:00.00 PM" #"04/17/2024 05:50:00.00 PM"#"03/19/2024 10:30:00.00 AM" #"03/19/2024 10:30:00.00 AM" #This is the Time when the Imported Measurement Dataframe data should stop
# -------------------------------------------------------------------------------------------------------------------------------------------------------

#Data Loading
MT = MT(MachineName, mode, ModelFrequency,log_file_name, Comp_Model, Input_Selection_Model, start_time, end_time, TemperatureSensors, Engineering_Know_SensorSet, Eval_SensorSet_Paper, EnergyToPower, indigTemp, cheap_Features, Raw_PowerData, EnergyToPower_NonSmoothedEnergy, Raw_indigTemp, Env_TempSensors, model_directory, Compensation_Steps, train_len)
del MachineName, mode, TemperatureSensors                   #deleting useless variable

#machineSpec=load_DataMachine.specs()     #acess to all machine data from Machine method


print("="*47 + " " + "Done" + " " + "="*47)







