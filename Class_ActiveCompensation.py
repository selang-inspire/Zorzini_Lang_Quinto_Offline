"""
Created 2024-03-27  17:00:00
@author: Mario Zorzini (mzorzini)
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from Class_DataFromInflux import InfluxDBQuery


class ActiveCompensation:
    '''
    This class simulates the OFFLINE timesteps of the machine
    - The machine data is loaded from the machine specific class
    - The data is split into train and test
    - The training data is normalized
    - The test data is normalized using the mean and std. dev. of the training data
    '''
    def __init__(self, Input, Error, MT_General, ModelFrequency, InfluxDB, TempSensorsnames, TemperatureSensors, Compensation_Steps):
        # Initialization
        self.TempSensors = TemperatureSensors # True if only Temperature sensors should be used
        self.TempSensorsNames = TempSensorsnames # Names of the Temperature Sensors #TODO: Change it to input names and not only temperature sensors
        self.InfluxDBQuery = InfluxDB # InfluxDB Query class
        self.MT_general = MT_General # Access to global MT_data, link to it
        self.Comp_Model = None  # initialize the model
        self.Input_train = Input
        self.Error_train = Error
        self.first = True #First time normalization, to get the mean and std. dev. of the training data
        self.ModelFrequency = ModelFrequency #Pause time between each model step
        # How many predictions should the model make (to not go to infinity)
        self.Compensation_Steps = Compensation_Steps
        self.Error_Corrections = None

    def Save_TrainData(self):
        '''
        - Only saves the data at the right directory
        '''
        # save in Datamanager
        self.MT_general.Train_Input_bucket = self.Input_train
        self.MT_general.Train_Output_bucket = self.Error_train

    def Start_Compensation(self):
        '''
        - This def will start the active compensation
        '''
        # Initialization of dictionaries used in this function--> maybe shift to init?
        self.MT_general.Full_Input_bucket = {key: pd.DataFrame() for key in self.Input_train.keys()}
        self.MT_general.Full_Predicted_bucket = {key: pd.DataFrame() for key in self.Input_train.keys()}
        self.MT_general.Predicted_bucket = {key: pd.DataFrame() for key in self.Input_train.keys()}
        self.MT_general.Test_Input_bucket = {key: pd.DataFrame() for key in self.Input_train.keys()}
        self.Comp_Model.TempSensors = self.TempSensors
        self.Comp_Model.PADDING_Timestamp = self.MT_general.Padding_Row_Indices

        for key in self.MT_general.Full_Input_bucket.keys():
            self.MT_general.Full_Input_bucket[key] = self.Input_train[key]
            # self.MT_general.Full_Predicted_bucket[key] = self.Comp_Model.Model_TrainPredict(self.Error_train[key], key) #TODO: Indeed not necessary for ONLINE
        # This part starts the prediction
        for step in range(self.Compensation_Steps):
            newest_prediction = {}
            self.get_actual_input(step)
            self.split_Inputs_to_dict(step)
            for key in self.MT_general.Full_Input_bucket.keys():
                if self.TempSensors: # Only Temp data has previous measurements available since the raspberry pi can work without the MT
                    self.Comp_Model.Previous_Input_beforeONLINECompensation = self.LastRecentTemp_dict[key] # previous values before compensation(only Temp)
                self.Comp_Model.Current_Test_Input = self.selected_input_test[key] # insert actual value into Model
                # print(f"Current Input: {self.Comp_Model.Current_Test_Input}") # for debugging
                self.Comp_Model.Pre_Model_ActivePredict_2(key)
                self.Comp_Model.Model_Predict(step, key)
                self.MT_general.Predicted_bucket[key] = pd.concat([self.MT_general.Predicted_bucket[key], self.Comp_Model.Current_predicted_Output])
                newest_prediction[key] = self.Comp_Model.Current_predicted_Output
            # check values if they are in an appropriate range
            for keys in newest_prediction.keys():
                value_in_mu = newest_prediction[keys]['Wert_4'][step]
                if value_in_mu > 1000:
                    print("\033[91mPrediction is too high, check the Input Data\033[0m")
                    breakpoint() # for debugging
                    #exit()
            self.Error_Corrections.insert_predictions(newest_prediction, step)
            self.InfluxDBQuery.influx_export_Prediction(newest_prediction)
            self.ModelStep()

    def get_actual_input(self, step):
        '''
        - This def will get the actual input data from the InfluxDB
        - The data is loaded from the InfluxDB and put into a nice table layout
        '''
        InputNames, time_res, time_res_energy, results = self.InfluxDBQuery.query(start_iso=None, end_iso=None)
        del time_res_energy
        Actual_Input_DF = self.MT_general.Table_Layout_Panda(time_res, InputNames, results)
        ###Only TempData
        if self.TempSensors:
            Temp_sensor_extract = ["Time"] + self.TempSensorsNames
            self.Actual_Input_DF = Actual_Input_DF.loc[:, Temp_sensor_extract]
            if step == 0:
                self.LastRecentTemp = self.Actual_Input_DF.drop(self.Actual_Input_DF.index[-1])
        else:
            self.Actual_Input_DF = Actual_Input_DF
        self.Actual_Input_DF = self.Actual_Input_DF.tail(1) # get newest one
        ###Only TempData end###
        self.current_time = self.Actual_Input_DF['Time'].iloc[-1] # get actual time

    def ModelStep(self):
        '''
        - checks if new measurement data should be loaded
        - Regulates the speed of the Compensation Model
        '''
        current_time = pd.to_datetime(self.current_time)
        # Add 30 seconds to the current time
        next_time = current_time + timedelta(seconds=self.ModelFrequency)
        # Wait until the next time is reached
        act_time = datetime.now()
        while next_time > act_time: # wait until next measurement input reached
            act_time = datetime.now()

    def split_Inputs_to_dict(self, step):
        '''
        - This def will split the input data into the dictionary
        - If InputSelection was made with training data, the selected inputs will be selected
        '''
        self.selected_input_test = {} #actual Input for each error

        if self.MT_general.Selected_Input_Names is not None:
            for key, columns in self.MT_general.Selected_Input_Names.items():
                Actual_Input_DF1 = self.Actual_Input_DF.copy()
                self.selected_input_test[key] = Actual_Input_DF1[columns]
        else:
            for key in self.MT_general.Full_Input_bucket.keys():
                actualDFCopy = self.Actual_Input_DF.copy()
                valid_columns = self.MT_general.Full_Input_bucket[key].columns
                actual_columns = actualDFCopy.columns
                columns_to_drop = [col for col in actual_columns if col not in valid_columns]
                actualDFCopy = actualDFCopy.drop(columns=columns_to_drop)
                self.selected_input_test[key] = actualDFCopy

        for key in self.MT_general.Full_Input_bucket.keys():
            # Nullen--> substract reference
            for column in self.selected_input_test[key].columns:
                if column != 'Time':
                    self.selected_input_test[key].loc[:, column] = self.selected_input_test[key][column] - self.MT_general.Reference_Input[key][column].values[0]
            self.MT_general.Test_Input_bucket[key] = pd.concat([self.MT_general.Test_Input_bucket[key], self.selected_input_test[key]])
        # ------------------------------------------------------------------------------------------------------------------------------------------------------------
        # Only for the first step to get the Temperature Data before the compensation starts for PADDING Temp Data
        if step == 0 and self.TempSensors:
            self.LastRecentTemp_dict = {}  # Null for each previous temp only for step==0
            if self.MT_general.Selected_Input_Names is not None:
                for key, columns in self.MT_general.Selected_Input_Names.items():
                    LastRecentTemp1 = self.LastRecentTemp.copy()
                    self.LastRecentTemp_dict[key] = LastRecentTemp1[columns]
            else:
                for key in self.MT_general.Full_Input_bucket.keys():
                    LastRecentTemp = self.LastRecentTemp.copy()
                    valid_columns = self.MT_general.Full_Input_bucket[key].columns
                    actual_columns = LastRecentTemp.columns
                    columns_to_drop = [col for col in actual_columns if col not in valid_columns]
                    LastRecentTemp = LastRecentTemp.drop(columns=columns_to_drop)
                    self.LastRecentTemp_dict[key] = LastRecentTemp
            for key in self.MT_general.Full_Input_bucket.keys():
                # Nullen--> substract reference
                for column in self.LastRecentTemp_dict[key].columns:
                    if column != 'Time':
                        self.LastRecentTemp_dict[key].loc[:, column] = self.LastRecentTemp_dict[key][column] - self.MT_general.Reference_Input[key][column].values[0]
        # check values if they are in an appropriate range
        for keys in self.LastRecentTemp_dict.keys():
            # Create a copy of the DataFrame excluding the 'Time' column
            df_without_time = self.LastRecentTemp_dict[keys].drop(columns='Time')
            # Check if any value in the DataFrame is smaller than -30 or bigger than 30
            if df_without_time.values.min() < -30 or df_without_time.values.max() > 30:
                print("\033[91mInput Data is not in an appropriate range\033[0m")
                breakpoint()  # for debugging
                # exit()
        self.Upload_Inputs_ToInflux() # Upload the actual input data to the InfluxDB

    def Upload_Inputs_ToInflux(self):
        '''
        Loads the actual input data to the InfluxDB
        '''
        for key in self.selected_input_test.keys():
            column_names = self.selected_input_test[key].columns.tolist()
            first_row_values = self.selected_input_test[key].iloc[0].tolist()
            self.InfluxDBQuery.influx_export_Inputs(column_names, first_row_values, key)

