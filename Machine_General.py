import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from colorama import Fore, Style
from threading import Thread
from Class_Machine_General_Data import Machine_Data
from Class_DataFromInflux import InfluxDBQuery
from Class_Simulation import Simulation
from Class_ActiveCompensation import ActiveCompensation
from Model import Model
from Input_Selection import Input_selection



class MT:
    '''
    - This class is the main class for running the compensation model
    - It is used to initialize the all classes and to run the compensation model
    '''
    def __init__(self, Name, mode,measurementFrequency,log_file_name, error_excel_Quinto, Comp_Model, Input_Selection_Model, start_time, end_time, model_noise):
        #Print Machine Information
        def print_machine_info(name, mode, measurement_frequency):
            '''
            Prints the machine information in a nice format into the console
            '''
            header_footer = '=' * 100 + '\n' + 'Thermo Comp Software\n' + '=' * 100 + '\n'
            machine_details = f'Machine Name: {Fore.GREEN}{name}{Style.RESET_ALL}\n' + '-' * 100 + '\n' + f'Mode: {Fore.BLUE}{mode}{Style.RESET_ALL}\n' + '-' * 100 + '\n' + f'Measurement Frequency: {Fore.RED}{measurement_frequency} Seconds{Style.RESET_ALL}\n' + '=' * 100
            print(header_footer + machine_details)

        print_machine_info(Name, mode, measurementFrequency)

        #Import Machine specific package depending on which machine is used
        self.ModelActive = False
        self.model_noise = model_noise
        self.InputSelectionActive = False
        self.MT_General_Data = Machine_Data()

        if Name == "EVO_Quinto":
            from Class_EVO_Quinto import EVO_Quinto
            self.Machine = EVO_Quinto(log_file_name)

        elif Name == "EVO_100":
            from Class_EVO_100 import EVO_100
            self.Machine = EVO_100()
        else:
            raise SystemExit('Error: Unknown Machine Specific Library currently implemented "EVO_Quinto", "EVO100" or .')

        self.InfluxDBQuery = InfluxDBQuery(self.Machine.token, self.Machine.url, self.Machine.org) #Takes Keys to InfluxDb from MT specific class

        #self.IP_Overwrite_File = "C:/Users/Admin.AGATHON-7OEU3S8/AppData/Local/Agathon_AG/IpInputOverwrite/IpInputOverwrite.txt"
        self.IP_Overwrite_File = "//192.168.250.1/IpInputOverwrite/IpInputOverwrite.txt"
        self.IP_Log_File   = "//192.168.250.1/Bins/IpInputLog4R.tmp"
        self.MachineName   = Name #which MT is used
        self.Mode          = mode #if Sim, Compensation or Log
        self.IP_Comp_Values = pd.DataFrame(columns=["Time"])
        self.Prediction = pd.DataFrame(columns=["Time","X Offset LR","Y Offset LR","Z Offset LR"])

        #Check if a compensation model or input selection model is selected
        if Comp_Model != None:
            self.ModelActive = True
            self.Model = Model()
            self.Model.ModelType = Comp_Model

        if self.ModelActive==False:
            print("No Model is active, no compensation possible, please select a model in the settings in the Main-File.")

        if Input_Selection_Model != None:
            self.InputSelectionActive = True
            self.InputSelection = Input_selection(self.MT_General_Data, Input_Selection_Model)

        if self.InputSelectionActive==False:
            print("No Input Selection is active")
            print('-'*100)

        #Define in which mode the software is running
        if mode == "Sim":
            self.ThermalError = {} #are dictionaries which contains pandaDf (Error data)
            self.Inputs = {} #are dictionaries which contains pandaDf (Input data)
            self.LoadTrainData(error_excel_Quinto, start_time, end_time)
            self.Simulation()

        elif mode == "Compensation" or mode == "Log":
            self.ThermalError = {} #are dictionaries which contains pandaDf (Training Error Data)
            self.Inputs = {} #are dictionaries which contains pandaDf (Training Input Data)
            self.LoadTrainData(error_excel_Quinto, start_time, end_time) #loads data into ThermalErro and Inputs
            self.Active_Compensation(measurementFrequency)
            #self.Machine.ConnectMachine(measurementFrequency) #TODO: in echter ONLINE umgebung dann auskommentieren 27/03/2024 16:33
            #thread = Thread(target = self.Machine.OPC.start(), daemon=True) #TODO: in echter ONLINE umgebung dann auskommentieren 27/03/2024 16:33
            #thread.start() #TODO: in echter ONLINE umgebung dann auskommentieren 27/03/2024 16:33
        else:
            raise SystemExit('Error: Unknown Machine Mode, currently implemented "Sim", "Compensation" or "Log".')


        #Test Arbitrary prediction values:
        self.Prediction.loc[0,"Time"] = datetime.now()
        self.Prediction.loc[0,"X Offset LR"] = -0.050#15
        self.Prediction.loc[0,"Y Offset LR"] = -0.0500#15
        self.Prediction.loc[0,"Z Offset LR"] = -0.0500#15
        self.Prediction.loc[0,"X Offset RR"] = -0.0500#15
        self.Prediction.loc[0,"Y Offset RR"] = -0.0500#15
        self.Prediction.loc[0,"Z Offset RR"] = -0.0500#15

        #self.Compensation_To_Machine() #auskommentiert aufgrund errormeldung 06/03/2024 #TODO: wohin kommt das in ONLINE implementation

        # Close the logger to ensure all logs are written to the file

    def LoadTrainData(self, error_excel_Quinto, start_time, end_time):
        '''
        - This def will be used to load the data from the MT specific Excel file stored in Class_<Name of the MT>.py and the InfluxDB
        - This data will be here preprocessed and stored in the MT_general_data class
        - The dat here is used for the simulation
        '''
        print("Begin loading Data")
        # Read in Error and Temp data (used later as training data)
        Extracted_Error_Excel, start_iso, end_iso, reference_error_dataframe = self.Machine.Load_Excel_Error(error_excel_Quinto, start_time, end_time, self.model_noise)
        self.MT_General_Data.Reference_Error = reference_error_dataframe.copy() #Store the reference 0 point of each error
        time_columns_dict = {key: df['Time'] for key, df in Extracted_Error_Excel.items()}
        self.MT_General_Data.error_data(time_columns_dict.copy(), None, Extracted_Error_Excel.copy())
        # Extract Temp_Data from InfluxDB
        self.MT_General_Data.temp_data(*self.InfluxDBQuery.query(start_iso, end_iso))
        Temperature_DF = self.MT_General_Data.Table_Layout_Panda(self.MT_General_Data.Global_Meas_Time_Temp, self.MT_General_Data.Temp_Sensornames, self.MT_General_Data.Temp_Values)
        # extract Temperature Sensors--> only Temp data here
        Temp_sensor_extract = ["Time"] + self.Machine.SensorList
        Temperature_DF = Temperature_DF.loc[:, Temp_sensor_extract]
        #Sample the Input data and stored it into sampled_dict
        sampled_InputDf = {}
        for key in time_columns_dict.keys():
            sampled_InputDf[key] = self.MT_General_Data.sample_dataframe(Temperature_DF.copy(), time_columns_dict[key].tolist())
        self.MT_General_Data.Sampled_InputData = sampled_InputDf.copy() #save it into the Datamanager
        #Store the data in Sim
        self.Inputs = sampled_InputDf.copy()
        self.ThermalError = Extracted_Error_Excel.copy()
        #Check if data is loaded correctly
        if not self.Inputs or not self.ThermalError:
            print("Error: Data not loaded correctly")
        else:
            print("Data successfully loaded")

    def Active_Compensation(self, measurementFrequency):
        #Initalization of the Active Compensation
        self.Class_Comp = ActiveCompensation(self.Inputs, self.ThermalError, self.MT_General_Data, measurementFrequency, self.InfluxDBQuery)
        # Load Data into Datamanager
        self.Class_Comp.Save_TrainData()
        # Initialize Model
        if self.ModelActive:
            self.Class_Comp.Comp_Model = self.Model
            self.Model.TrainData_Output = self.MT_General_Data.Train_Output_bucket
        # Input Selection
        if self.InputSelectionActive:
            self.MT_General_Data.SelectedInputs_Train = {}
            self.MT_General_Data.Selected_Input_Names = {}
            for key in self.MT_General_Data.Train_Input_bucket.keys():
                selected_inputs_train, selected_input_names = self.InputSelection.InputSelectionModel(self.MT_General_Data.Train_Input_bucket[key], self.MT_General_Data.Train_Output_bucket[key])
                self.MT_General_Data.SelectedInputs_Train[key] = selected_inputs_train
                self.MT_General_Data.Selected_Input_Names[key] = selected_input_names
            self.Class_Comp.Input_train = self.MT_General_Data.SelectedInputs_Train
            print("Input Selection is successfully completed")
        # Generate Model
        if self.ModelActive and self.InputSelectionActive == True:
            self.Model.TrainData_Input = self.MT_General_Data.SelectedInputs_Train
        if self.ModelActive and self.InputSelectionActive == False:
            self.Model.TrainData_Input = self.MT_General_Data.Train_Input_bucket
        # Active Compensation Starts here
        if self.ModelActive:
            self.Model.Generate()
            self.Class_Comp.Start_Compensation()
            print("Compensation successfully completed")
        else:
            print("Model is not active, no compensation possible")


    def Simulation(self):
        '''
        - This def will be used to simulate the architecture of the compensation model in a OFFLINE environment
        '''
        # Initalization of the Simulation
        self.Class_Sim = Simulation(self.Inputs, self.ThermalError, self.MT_General_Data)
        # Preparation Simulation
        self.Class_Sim.Split_Train_Test() #Split the data into train and test
        #Initialize Model
        if self.ModelActive:
            self.Class_Sim.Comp_Model = self.Model
            self.Model.TrainData_Output = self.MT_General_Data.Train_Output_bucket
        #Input Selection
        if self.InputSelectionActive:
            self.MT_General_Data.SelectedInputs_Train = {}
            self.MT_General_Data.Selected_Input_Names = {}
            for key in self.MT_General_Data.Train_Input_bucket.keys():
                selected_inputs_train, selected_input_names = self.InputSelection.InputSelectionModel(self.MT_General_Data.Train_Input_bucket[key], self.MT_General_Data.Train_Output_bucket[key])
                self.MT_General_Data.SelectedInputs_Train[key] = selected_inputs_train
                self.MT_General_Data.Selected_Input_Names[key] = selected_input_names
            self.Class_Sim.Input_train = self.MT_General_Data.SelectedInputs_Train
            selected_input_test = {}
            for key, columns in self.MT_General_Data.Selected_Input_Names.items():
                selected_input_test[key] = self.Class_Sim.Input_test[key][columns]
            self.Class_Sim.Input_test = selected_input_test
            print("Input Selection is successfully completed")
        #Generate Model
        if self.ModelActive and self.InputSelectionActive==True:
            self.Model.TrainData_Input = self.MT_General_Data.SelectedInputs_Train
        if self.ModelActive and self.InputSelectionActive==False:
            self.Model.TrainData_Input = self.MT_General_Data.Train_Input_bucket
        #Simulate Starts here
        if self.ModelActive:
            self.Model.Generate()
            self.Class_Sim.Start_Simulation()
            self.Model.RMSE_Calculation_OFFLINE(self.MT_General_Data)
            self.Model.plot_comp_results_OFFLINE(self.MT_General_Data)
            print("Simulation successfully completed")
        else:
            print("Model is not active, no compensation possible")

    def Read_State_Interpreter(self):
        #Read previous status from IP
        logf = open(self.IP_Log_File,"r")
        IP_Params = logf.read()
        entries = IP_Params.split(";")
        # Create a list to hold the name-value pairs
        name_value_pairs = []
        # Process each entry
        for entry in entries:
            if "=" in entry:  # Check if the entry contains an '=' sign
                name, value = entry.split(" = ")
                name_value_pairs.append((name.strip(), value.strip()))
                if name == "\nXOffsCorr4LR":
                    Xnr = len(name_value_pairs)-1
                if name == "\nXOffsCorr4RR":
                    Xnr_RR = len(name_value_pairs)-1

        locnr = len(self.IP_Comp_Values)
        self.IP_Comp_Values.loc[locnr,"Time"] = datetime.now()
        self.IP_Comp_Values.loc[locnr,"X Offset LR"] = float(name_value_pairs[Xnr][1])        
        self.IP_Comp_Values.loc[locnr,"Y Offset LR"] = float(name_value_pairs[Xnr+1][1])        
        self.IP_Comp_Values.loc[locnr,"Z Offset LR"] = float(name_value_pairs[Xnr+2][1])        
        self.IP_Comp_Values.loc[locnr,"X Offset RR"] = float(name_value_pairs[Xnr_RR][1])        
        self.IP_Comp_Values.loc[locnr,"Y Offset RR"] = float(name_value_pairs[Xnr_RR+1][1])        
        self.IP_Comp_Values.loc[locnr,"Z Offset RR"] = float(name_value_pairs[Xnr_RR+2][1])        

        #TODO Incorporate anvil pivot values that make sens

    def Write_Interpreter_Overwrite(self):
        f = open(self.IP_Overwrite_File,"r+")
        contents = f.read() #Read all content, currently not used, contents new writes independent of old
        #Delete all content
        f.truncate(0)
        #Define ofsset to correct
        locnr = len(self.Prediction)-1
        X_LR =  "\nXOffsCorr4LR = " + str(self.Prediction.loc[locnr,"X Offset LR"]+self.IP_Comp_Values.loc[0,"X Offset LR"]) + " ;" +"\n"
        X_RR =  "XOffsCorr4RR = " + str(self.Prediction.loc[locnr,"X Offset RR"]+self.IP_Comp_Values.loc[0,"X Offset RR"]) + " ;" +"\n"
        Y_LR = "YOffsCorr4LR = " + str(self.Prediction.loc[locnr,"Y Offset LR"]+self.IP_Comp_Values.loc[0,"Y Offset LR"]) + " ;" +"\n"
        Y_RR = "YOffsCorr4RR = " + str(self.Prediction.loc[locnr,"Y Offset RR"]+self.IP_Comp_Values.loc[0,"Y Offset RR"]) + " ;" +"\n"
        Z_LR = "ZOffsCorr4LR = " + str(self.Prediction.loc[locnr,"Z Offset LR"]+self.IP_Comp_Values.loc[0,"Z Offset LR"]) + " ;" +"\n" 
        Z_RR = "ZOffsCorr4RR = " + str(self.Prediction.loc[locnr,"Z Offset RR"]+self.IP_Comp_Values.loc[0,"Z Offset RR"]) + " ;" +"\n" 
        contents_new = X_LR+Y_LR+Z_LR+X_RR+Y_RR+Z_RR
        #Write Compensation TxT
        f.write(contents_new)
        f.close()


    def Compensation_To_Machine(self):
        #TODO IP input overwrite

        #Read Current Interpreter values and safe them and the time in IP_Comp_Values
        self.Read_State_Interpreter()
        #ReadTxt from overwrite file, which is subsequently modified
        self.Write_Interpreter_Overwrite()




