#Thermal compensation Main Python Implementation
#Author: Sebastian Lang

import pandas as pd
import numpy as np

#IMPORTANT: Currently The HMI has to be run as admin to allow the Compensation file sharing to work!

#Parameters setting
from Machine_General import MT
import matplotlib
matplotlib.use('TkAgg') #used for the plot to be shown in a window

MachineName = "EVO_Quinto"            #machine name
mode        = "Compensation"                   #set mode we are working with, either Sim or Compensation, or Log? TODO Log is supposed to be Online but without writing
measurementFrequency=30 #Measurement frequency in seconds for read-in of data
log_file_name = "C:\\Users\\Admin.AGATHON-7OEU3S8\\Desktop\\MainThermokompensation\\Messdaten\\Log_AP_22_02_2024.csv"
Logfrequency=1 #TODO Log only at logfrequency, measure and aggregate average/filter? at measurementFrequency currently not implemented
Comp_Model = 'ARDL' #None, "ARDL", "FFNN", "LSTM" define which Model to use for compensation
Input_Selection_Model = 'LASSO' #None, 'LASSO', 'Group LASSO'
Model_Noise = False #True: Noise will be added, False: No Noise

######Excel Error File & Time Settings######
error_excel_Quinto = r'C:\Users\mzorzini\OneDrive - ETH Zurich\Zorzini_Inspire\Semester_Project\02_Measurements\Error_Measurements\B3_Endless_Inspire - 2024-03-19 11.36.04.270.xlsx'
start_time = "03/18/2024 04:10:00.00 PM" #This is the Time when the Imported Measurement Dataframe data should start to bea read in--> e.g. Training Dataframe for ONLINE, or whole Dataset for OFFLINE
end_time = "03/18/2024 11:00:00.00 PM" #"03/19/2024 10:59:59.00 AM" #This is the Time when the Imported Measurement Dataframe data should stop
#############################################
# TODO? Move all to settings variable

#Data Loading
MT = MT(MachineName, mode, measurementFrequency,log_file_name, error_excel_Quinto, Comp_Model, Input_Selection_Model, start_time, end_time, Model_Noise)
del MachineName, mode, error_excel_Quinto                     #deleting useless variable

#machineSpec=load_DataMachine.specs()     #acess to all machine data from Machine method


print("="*47 + " " + "Done" + " " + "="*47)









