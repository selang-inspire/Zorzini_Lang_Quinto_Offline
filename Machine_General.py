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
from Class_FeatureProcessing import FeatureProcessing
from Class_AGATHON_Com import AGATHON_Com
import os
import pickle



class MT:
    '''
    - This class is the main class for running the compensation model
    - It is used to initialize the all classes and to run the compensation model
    - This is the actual "Main" class
    '''
    def __init__(self, Name, mode,ModelFrequency,log_file_name, Comp_Model, Input_Selection_Model, start_time, end_time, TemperatureSensors, Engineering_Know_SensorSet, Eval_SensorSet_Paper, EnergyToPower, indigTemp, cheap_Features, Raw_PowerData, EnergyToPower_NonSmoothedEnergy, Raw_indigTemp, Env_TempSensors, model_directory, Compensation_Steps, train_len, save_load_model, LogInfluxFrequency, measurementFrequency):
        #Print Machine Information
        def print_machine_info(name, mode, measurement_frequency):
            '''
            Prints the machine information in a nice format into the console
            '''
            header_footer = '=' * 100 + '\n' + 'Thermo Comp Software\n' + '=' * 100 + '\n'
            machine_details = f'Machine Name: {Fore.GREEN}{name}{Style.RESET_ALL}\n' + '-' * 100 + '\n' + f'Mode: {Fore.BLUE}{mode}{Style.RESET_ALL}\n' + '-' * 100 + '\n' + f'Model Frequency: {Fore.RED}{measurement_frequency} Seconds{Style.RESET_ALL}\n' + '=' * 100
            print(header_footer + machine_details)

        print_machine_info(Name, mode, ModelFrequency)

        #Import Machine specific package depending on which machine is used
        self.ModelActive = False
        self.LogInfluxFrequency = LogInfluxFrequency
        self.InputSelectionActive = False
        self.TempSensors = TemperatureSensors
        self.EnergyToPower = EnergyToPower
        self.indigTemp = indigTemp
        self.raw_indigTemp = Raw_indigTemp
        self.RawPowerData = Raw_PowerData
        self.EnergyToPower_NonSmoothedEnergy = EnergyToPower_NonSmoothedEnergy
        self.cheap_Features = cheap_Features
        self.Engineering_Know_SensorSet = Engineering_Know_SensorSet
        self.Eval_SensorSet_Paper = Eval_SensorSet_Paper
        self.EnvTempSensors = Env_TempSensors
        self.MT_General_Data = Machine_Data()

        # Import the machine specific class here
        if Name == "EVO_Quinto":
            from Class_EVO_Quinto import EVO_Quinto
            self.Machine = EVO_Quinto(log_file_name)

        elif Name == "EVO_100":
            from Class_EVO_100 import EVO_100
            self.Machine = EVO_100()
        else:
            raise SystemExit('Error: Unknown Machine Specific Library currently implemented "EVO_Quinto", "EVO100" or .')

        # Initialize the InfluxDBQuery class with the corresponding keys which are stored in the Machine specific class
        self.InfluxDBQuery = InfluxDBQuery(self.Machine.token, self.Machine.url, self.Machine.org, self.Machine.queryName) #Takes Keys to InfluxDb from MT specific class

        #self.IP_Overwrite_File = "C:/Users/Admin.AGATHON-7OEU3S8/AppData/Local/Agathon_AG/IpInputOverwrite/IpInputOverwrite.txt"
        self.IP_Overwrite_File = "//192.168.250.1/IpInputOverwrite/IpInputOverwrite.txt"
        self.IP_Log_File   = "//192.168.250.1/Bins/IpInputLog4R.tmp"
        self.MachineName   = Name #which MT is used
        self.Mode          = mode #if Sim, Compensation or Log
        self.IP_Comp_Values = pd.DataFrame(columns=["Time"])
        self.AGATHON_Com = AGATHON_Com(self.IP_Log_File, self.IP_Overwrite_File)

        #Check if a compensation model or input selection model is selected
        if Comp_Model != None:
            self.ModelActive = True
            self.Model = Model()
            self.Model.MT_data = self.MT_General_Data
            self.Model.ModelType = Comp_Model
            self.Model.model_directory = model_directory
            self.Model.save_load_model = save_load_model

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
            self.Model.ONLINE = False #False that Model knows that it should not use PADDING vectors
            self.ThermalError = {} #are dictionaries which contains pandaDf (Error data)
            self.Inputs = {} #are dictionaries which contains pandaDf (Input data)
            self.LoadTrainData(start_time, end_time)
            self.MT_General_Data.Padding_Row_Indices, self.MT_General_Data.time_jump_indices = self.apply_time_jumps() #Timestamps where a jump occurs for each key
            self.TrainLen = train_len
            self.Simulation()

        elif mode == "Compensation" or mode == "Log":
            self.Model.ONLINE = True #True that Model knows that it should use PADDING vectors
            self.Compensation_Steps = Compensation_Steps #How many predictions are made (multiple of model Frequency)
            self.ThermalError = {} #are dictionaries which contains pandaDf (Training Error Data)
            self.Inputs = {} #are dictionaries which contains pandaDf (Training Input Data)
            # self.Machine.ConnectMachine(measurementFrequency,self.LogInfluxFrequency) #TODO: in echter ONLINE umgebung dann auskommentieren 27/03/2024 16:33
            # thread = Thread(target = self.Machine.OPC.start(), daemon=True) #TODO: in echter ONLINE umgebung dann auskommentieren 27/03/2024 16:33
            # thread.start() #TODO: in echter ONLINE umgebung dann auskommentieren 27/03/2024 16:33
            self.LoadTrainData(start_time, end_time) #loads data into ThermalErro and Inputs
            self.MT_General_Data.Padding_Row_Indices, self.MT_General_Data.time_jump_indices = self.apply_time_jumps() #Timestamps where a jump occurs for each key
            self.Active_Compensation(ModelFrequency)
        else:
            raise SystemExit('Error: Unknown Machine Mode, currently implemented "Sim", "Compensation" or "Log".')


    def LoadTrainData(self, start_time, end_time):
        '''
        - This def will be used to load the data from the MT specific Excel file stored in Class_<Name of the MT>.py and the InfluxDB
        - This data will be here preprocessed and stored in the MT_general_data class
        - The dat here is used for the simulation
        - TemperatureDF contains the Input data, not only Temperature but also Power etc.
        '''
        print("Begin loading Data")
        # Read in Error and Temp data (used later as training data)
        #Get start & end times in influx readable format
        start_iso, end_iso = self.InfluxDBQuery.Load_ISO_Time(start_time, end_time)
        #Get Displacement Measurements from InfluxDB
        PosNames_x, time_res_x, results_x, PosNames_y, time_res_y, results_y = self.InfluxDBQuery.position_query(start_iso, end_iso)
        time_res_x = [('temperature', *t[1:]) if t[0] == 'X' else t for t in time_res_x] #else TableLayout will not convert Time into right format (see self.MT_General_Data.Table_Layout_Panda)
        time_res_y = [('temperature', *t[1:]) if t[0] == 'Y' else t for t in time_res_y] #else TableLayout will not convert Time into right format
        DisplData_X = self.MT_General_Data.Table_Layout_Panda(time_res_x, PosNames_x, results_x)
        DisplData_Y = self.MT_General_Data.Table_Layout_Panda(time_res_y, PosNames_y, results_y)
        Extracted_Error_Excel, reference_error_dataframe = self.Machine.Calculate_Error(DisplData_X, DisplData_Y)
        ##################################
        self.MT_General_Data.Reference_Error = reference_error_dataframe.copy() #Store the reference 0 point of each error
        time_columns_dict = {key: df['Time'] for key, df in Extracted_Error_Excel.items()}
        self.MT_General_Data.error_data(time_columns_dict.copy(), None, Extracted_Error_Excel.copy())
        ##################################
        print("begin loading Input data from InfluxDB")
        # Load / Store the data from a pickle file
        store = True
        # Check if the file already exists
        if store == True:
            directory = r"C:\Users\mzorzini\OneDrive - ETH Zurich\Zorzini_Inspire\Semester_Project\02_Measurements\Temperature_Measurements"
            filename = "data.pkl"
            filepath = os.path.join(directory, filename)
            if os.path.exists(filepath):
                # Load the data from the pickle file
                    with open(filepath, 'rb') as f:
                        data = pickle.load(f)
                    self.MT_General_Data.Global_Meas_Time_Temp, self.MT_General_Data.Input_Sensornames, self.MT_General_Data.Temp_Values, self.MT_General_Data.Global_Meas_Time_Energy = data
            else:
                # Save the data to a pickle file
                self.MT_General_Data.temp_data(*self.InfluxDBQuery.query(start_iso, end_iso))
                if store == True:
                    data = (self.MT_General_Data.Global_Meas_Time_Temp, self.MT_General_Data.Input_Sensornames, self.MT_General_Data.Temp_Values, self.MT_General_Data.Global_Meas_Time_Energy)
                    with open(filepath, 'wb') as f:
                        pickle.dump(data, f)
        else:
            self.MT_General_Data.temp_data(*self.InfluxDBQuery.query(start_iso, end_iso))
        ##################################
        Temperature_DF = self.MT_General_Data.Table_Layout_Panda(self.MT_General_Data.Global_Meas_Time_Temp, self.MT_General_Data.Input_Sensornames, self.MT_General_Data.Temp_Values)
        ########Feature processing########
        if self.cheap_Features:
            self.FeatureProcessingClass = FeatureProcessing(Temperature_DF, self.MT_General_Data, self.Machine.SensorList, self.Mode, self.Machine.EnergySet, self.Machine.PowerSet, self.Machine.IndigTempSet)
        # decide which Input Data you want to go on with
            if self.EnergyToPower and not self.indigTemp:
                Features = self.MT_General_Data.processed_Power_Data
            elif self.indigTemp and not self.EnergyToPower:
                Features = self.MT_General_Data.processed_indigenous_temperature_data
            elif self.RawPowerData:
                Features = self.MT_General_Data.Raw_Power_Data
            elif self.EnergyToPower_NonSmoothedEnergy:
                Features = self.MT_General_Data.processed_Power_withoutSmoothedEnergy
            elif self.raw_indigTemp:
                Features = self.MT_General_Data.Raw_Indigenous_Temperature_Data
            elif self.EnergyToPower and self.indigTemp:
                processed_power_data = self.MT_General_Data.processed_Power_Data.copy()
                processed_indigenous_temperature_data = self.MT_General_Data.processed_indigenous_temperature_data.copy()
                processed_indigenous_temperature_data.drop(columns=["Time"], inplace=True)
                Features = pd.concat([processed_power_data, processed_indigenous_temperature_data], axis=1)
            else:
                raw_power_data = self.MT_General_Data.Raw_Power_Data.copy()
                raw_indigenous_temperature_data = self.MT_General_Data.Raw_Indigenous_Temperature_Data.copy()
                raw_indigenous_temperature_data.drop(columns=["Time"], inplace=True)
                Features = pd.concat([raw_power_data, raw_indigenous_temperature_data], axis=1)
            CheapData = Features
        ######################################################
        # extract Temperature Sensors--> only Temp data here
        if self.TempSensors:
            if self.Engineering_Know_SensorSet:
                Temp_sensor_extract = ["Time"] + self.Machine.EngKnowSensorSet
            elif self.Eval_SensorSet_Paper:
                Temp_sensor_extract = ["Time"] + self.Machine.EvalSensorSet
            elif self.EnvTempSensors:
                Temp_sensor_extract = ["Time"] + self.Machine.EnvTempSensorsSet
            else:
                Temp_sensor_extract = ["Time"] + self.Machine.SensorList
            ExpensiveData = Temperature_DF.loc[:, Temp_sensor_extract]
        ######################################################
        #combines right data together
        if self.TempSensors and self.cheap_Features:
            if len(ExpensiveData) > len(CheapData):
                time_column = CheapData['Time']
                sampled_Data = self.MT_General_Data.sample_dataframe(ExpensiveData.copy(), time_column.tolist())
                CheapData.drop(columns=["Time"], inplace=True)
                Temperature_DF = pd.concat([sampled_Data, CheapData], axis=1)
            else:
                time_column = ExpensiveData['Time']
                sampled_Data = self.MT_General_Data.sample_dataframe(CheapData.copy(), time_column.tolist())
                sampled_Data.drop(columns=["Time"], inplace=True)
                Temperature_DF = pd.concat([ExpensiveData, sampled_Data], axis=1)

        elif self.TempSensors and not self.cheap_Features:
            Temperature_DF = ExpensiveData
        elif self.cheap_Features and not self.TempSensors:
            Temperature_DF = CheapData
        ######################################################
        #Getting Input before sampling to error data
        unsampled_InputDf = {}
        for key in time_columns_dict.keys():
            unsampled_InputDf[key] = Temperature_DF.copy()
        ######################################################
        #Sample the Input data and stored it into sampled_dict
        sampled_InputDf = {}
        for key in time_columns_dict.keys():
            sampled_InputDf[key] = self.MT_General_Data.sample_dataframe(Temperature_DF.copy(), time_columns_dict[key].tolist())
        ######################################################
        ####################refrence Input Values####################
        # Initialize the dictionary
        self.MT_General_Data.Reference_Input = {}
        for key, df in sampled_InputDf.items():
            # Copy the DataFrame associated with the current key
            sampled_df = df.copy()
            # Create a reference input value from the first row of the DataFrame
            reference_input_values = pd.DataFrame([sampled_df.iloc[0].tolist()], columns=sampled_df.columns.tolist())
            # Store the reference input value in the dictionary
            self.MT_General_Data.Reference_Input[key] = reference_input_values.copy()
            # Subtract the reference from all other rows in the DataFrame
            for column in sampled_df.columns:
                if column != 'Time':
                    sampled_df[column] = sampled_df[column] - reference_input_values[column].values[0]
            # Store the modified DataFrame back into the dictionary
            sampled_InputDf[key] = sampled_df
        #For original Input Dataframe--> nullen
        for key, df in unsampled_InputDf.items():
            unsampled_DF = df.copy()
            for column in unsampled_DF.columns:
                if column != 'Time':
                    unsampled_DF[column] = unsampled_DF[column] - self.MT_General_Data.Reference_Input[key][column].values[0]
            unsampled_InputDf[key] = unsampled_DF
        self.MT_General_Data.orig_InputData = unsampled_InputDf.copy()
        ######################################################
        self.MT_General_Data.Sampled_InputData = sampled_InputDf.copy()
        #Store the data in Sim
        self.Inputs = sampled_InputDf.copy()
        self.ThermalError = Extracted_Error_Excel.copy()

        #Check if data is loaded correctly
        if not self.Inputs or not self.ThermalError:
            print("Error: Data not loaded correctly")
        else:
            print("Data successfully loaded")
        print('='*100)

    def find_time_jumps(self, df):
        '''
        - calculates the time jumps in the data
        - if difference bigger than 10 minutes, it is recognized as a time jump
        - Therefore Padding is necessary!
        return:
        list of time, where the jump occurs (e.g. 17:05:00 diff with 17:30:00, it will return 17:30:00, else nothing)
        '''
        time_jumps = []
        time_jump_indices = []
        df['Time'] = pd.to_datetime(df['Time'])
        time_column = df['Time']
        for i in range(len(time_column) - 1):
            time_diff = time_column.iloc[i + 1] - time_column.iloc[i]
            if time_diff.total_seconds() > 10 * 60:
                time_jumps.append(time_column.iloc[i + 1])
                time_jump_indices.append(i + 1)
                print('Time jump detected (> 10min): PADDING necessary')
                print(time_column.iloc[i])
                print(time_column.iloc[i + 1])
                print('-' * 100)
        return time_jumps, time_jump_indices

    def apply_time_jumps(self):
        '''
        manages the time jumps in the data for each key (each error)
        --> more explanation in def find_time_jumps
        '''
        time_jumps_dict = {}
        time_jump_indices_dict = {}
        for key in self.Inputs:
            df = self.Inputs[key]
            time_jumps, time_jump_indices = self.find_time_jumps(df)
            time_jumps_dict[key] = time_jumps
            time_jump_indices_dict[key] = time_jump_indices
        return time_jumps_dict, time_jump_indices_dict

    def Active_Compensation(self, ModelFrequency):
        '''
        - This def will be used to run the architecture of the compensation model in a ONLINE environment
        '''
        #Initalization of the Active Compensation
        #Input_names = [col for col in self.Inputs.columns if col != 'Time']
        self.Class_Comp = ActiveCompensation(self.Inputs, self.ThermalError, self.MT_General_Data, ModelFrequency, self.InfluxDBQuery, self.Machine.SensorList, self.TempSensors, self.Compensation_Steps)
        # For Error Feedback to MT
        self.Class_Comp.Error_Corrections = self.AGATHON_Com
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
                selected_inputs_train, selected_input_names = self.InputSelection.InputSelectionModel(self.MT_General_Data.Train_Input_bucket[key], self.MT_General_Data.Train_Output_bucket[key], self.MT_General_Data.time_jump_indices[key])
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
        - The structure is similar to active compensation but instead of class Active Compensation it will call the class Simulation
        '''
        # Initalization of the Simulation
        self.Class_Sim = Simulation(self.Inputs, self.ThermalError, self.MT_General_Data, self.TempSensors)
        # Preparation Simulation
        self.Class_Sim.Split_Train_Test(self.TrainLen) #Split the data into train and test
        # Initialize Model
        if self.ModelActive:
            self.Class_Sim.Comp_Model = self.Model
            self.Model.TrainData_Output = self.MT_General_Data.Train_Output_bucket
        # Input Selection
        if self.InputSelectionActive:
            self.MT_General_Data.SelectedInputs_Train = {}
            self.MT_General_Data.Selected_Input_Names = {}
            for key in self.MT_General_Data.Train_Input_bucket.keys():
                selected_inputs_train, selected_input_names = self.InputSelection.InputSelectionModel(self.MT_General_Data.Train_Input_bucket[key], self.MT_General_Data.Train_Output_bucket[key], self.MT_General_Data.time_jump_indices[key])
                self.MT_General_Data.SelectedInputs_Train[key] = selected_inputs_train
                self.MT_General_Data.Selected_Input_Names[key] = selected_input_names
            self.Class_Sim.Input_train = self.MT_General_Data.SelectedInputs_Train
            selected_input_test = {}
            for key, columns in self.MT_General_Data.Selected_Input_Names.items():
                selected_input_test[key] = self.Class_Sim.Input_test[key][columns]
            self.Class_Sim.Input_test = selected_input_test
            print("Input Selection is successfully completed")
        # Update Input for unsamples original Input data which was not sampled acc. to error data
        if self.InputSelectionActive:
            for key, columns in self.MT_General_Data.Selected_Input_Names.items():
                self.MT_General_Data.orig_InputData[key] = self.MT_General_Data.orig_InputData[key][columns]
        # Generate Model
        if self.ModelActive and self.InputSelectionActive==True:
            self.Model.TrainData_Input = self.MT_General_Data.SelectedInputs_Train
        if self.ModelActive and self.InputSelectionActive==False:
            self.Model.TrainData_Input = self.MT_General_Data.Train_Input_bucket
        # Simulate Starts here
        if self.ModelActive:
            self.Model.Generate()
            self.Class_Sim.Start_Simulation()
            self.Model.RMSE_Calculation_OFFLINE(self.MT_General_Data)
            Energy = False
            if self.EnergyToPower or self.RawPowerData or self.EnergyToPower_NonSmoothedEnergy and not self.EnvTempSensors:
                Energy = True
            if Energy and self.TempSensors == False and self.indigTemp == False and self.raw_indigTemp == False:
                self.Model.plot_comp_results_OnlyPower_OFFLINE(self.MT_General_Data)
            else:
                self.Model.plot_comp_results_OFFLINE(self.MT_General_Data)
            print("Simulation successfully completed")
        else:
            print("Model is not active, no compensation possible")






