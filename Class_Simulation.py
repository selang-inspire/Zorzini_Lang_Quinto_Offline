'''
Author: Mario Zorzini (mzorzini)
date: 2024-03-12
'''
import pandas as pd
import datetime
import numpy as np


class Simulation:
    '''
    This class simulates the OFFLINE timesteps of the machine
    - The machine data is loaded from the machine specific class
    - The data is split into train and test
    - The training data is normalized
    - The test data is normalized using the mean and std. dev. of the training data
    '''
    def __init__(self, Input, Error, MT_General, TemperatureSensors):
        #Initialization
        self.TempSensors = TemperatureSensors #True if only Temperature sensors should be used
        self.MT_general = MT_General #Access to global MT_data, link to it
        self.Comp_Model = None  # initialize the model
        self.Input = Input
        self.Error = Error
        self.first = True #First time normalization, to get the mean and std. dev. of the training data

    def Split_Train_Test(self, TrainLen):
        '''
        - Train/Test Split function of sklearn uses random order therefore not used
        - The first 80% of the data is used for training (if TrainLen is set to 0.8), can be adjusted, values need to be between 0 and 1
        - then, the last 20% of the data is used for testing
        '''
        train_len = TrainLen#0.35 #0.8
        self.Input_train = {}
        self.Error_train = {}
        self.Input_test = {}
        self.Error_test = {}
        for key in self.Input.keys():
            train_size_input = int(len(self.Input[key]) * train_len)
            self.Input_train[key] = self.Input[key][:train_size_input]
            self.Input_test[key] = self.Input[key][train_size_input:]
        for key in self.Error.keys():
            train_size_output = int(len(self.Error[key]) * train_len)
            self.Error_train[key] = self.Error[key][:train_size_output]
            self.Error_test[key] = self.Error[key][train_size_output:]
        # save in Datamanager
        self.MT_general.Train_Input_bucket = self.Input_train #maybe add .copy() to avoid changing the original data
        self.MT_general.Train_Output_bucket = self.Error_train
        self.MT_general.Test_Output_bucket = self.Error_test
        self.MT_general.Test_Original_Input_bucket = self.Input_test


    def Input_Train_normalize(self): #Not used, only useful if you want normalizing error data
        '''
        The order of the Code here is important, else the normalization will not work
        - self.first equal True means that the mean and std. dev. is saved for further normalization, else new mean and std. dev. is calculated
        '''
        self.first = True
        self.Output_train_normalized = self.MT_general.z_score_normalization(self.Error_train, self.first)
        self.first = False
        self.Output_test_normalized = self.MT_general.z_score_normalization(self.Error_test, self.first)
        self.first = True
        self.Input_train_normalized = self.MT_general.z_score_normalization(self.Input_train, self.first)
        self.first = False

    def Input_Test_normalize(self): #Not used
        self.Input_test_normalized = self.MT_general.z_score_normalization(self.Input_test, self.first)

    def Start_Simulation(self):
        '''
        This function simulates the timesteps of the machine
        - It takes the training data and simulates the timesteps
        - The data is normalized and then added to the input bucket
        - The mean and std. dev. of the training data is used for the normalization of the test data
        '''
        # Initialize the dictionary else it will not work
        self.MT_general.Full_Input_bucket = {key: pd.DataFrame() for key in self.Input_test.keys()}
        self.MT_general.Full_Predicted_bucket = {key: pd.DataFrame() for key in self.Input_test.keys()}
        self.MT_general.Predicted_bucket = {key: pd.DataFrame() for key in self.Input_test.keys()}
        #If the padding is not set, set it to False--> initialize here all to False
        self.Comp_Model.PAD = {key: False for key in self.Input_test.keys()}
        self.Comp_Model.TempSensors = self.TempSensors
        # Simulate the timesteps
        for key in self.Input_test.keys():
            self.Comp_Model.Timestamp = None
            if self.TempSensors:  # Only Temp data has previous measurements available since the raspberry pi can work without the MT
                Original_PandaDF = self.MT_general.orig_InputData[key]  # previous values before compensation(only Temp)
                Original_InputData_dict =  {str(i): i for i in self.MT_general.Padding_Row_Indices[key]}
                # Get the previous values of the temperature sensors before PADDING starts
                for sub_key in Original_InputData_dict.keys():
                    Original_InputData_dict[sub_key] = Original_PandaDF.copy()
                    Original_InputData_dict[sub_key].set_index('Time', inplace=True)
                    Original_InputData_dict[sub_key].index = pd.to_datetime(Original_InputData_dict[sub_key].index)
                    sub_key_datetime = pd.to_datetime(sub_key)
                    differences = np.abs(Original_InputData_dict[sub_key].index - sub_key_datetime)
                    differences = differences.total_seconds()
                    nearest_index = differences.argmin()
                    Original_InputData_dict[sub_key] = Original_PandaDF.copy()
                    mask = Original_InputData_dict[sub_key].index < nearest_index
                    Original_InputData_dict[sub_key] = Original_InputData_dict[sub_key][mask]
                    #Original_InputData_dict[sub_key].drop('Time', axis=1, inplace=True)
                self.Comp_Model.Original_InputData = Original_InputData_dict
            self.Comp_Model.Current_and_previous_Input = None
            for i in range(len(self.Input_test[key])):
                # save in Datamanager to be used for the comp. model
                self.MT_general.Test_Input_bucket = self.Input_test[key].iloc[[i]] #Actual Input
                # Concatenate the data & save in full input bucket
                if i == 0:
                    self.MT_general.Full_Input_bucket[key] = self.Input_train[key]
                    self.MT_general.Full_Predicted_bucket[key] = self.Comp_Model.Model_TrainPredict(self.Error_train[key], key)
                self.MT_general.Full_Input_bucket[key] = pd.concat([self.MT_general.Full_Input_bucket[key], self.MT_general.Test_Input_bucket])
                print(self.MT_general.Test_Input_bucket)
                # Calls the model to predict the output & Save in MT General Data
                self.Comp_Model.Current_Test_Input = self.MT_general.Test_Input_bucket
                self.Comp_Model.Pre_Model_ActivePredict_2(key)  # Calls the compensation model to predict the output
                self.Comp_Model.Model_Predict(i, key)
                self.MT_general.Predicted_bucket[key] = pd.concat([self.MT_general.Predicted_bucket[key], self.Comp_Model.Current_predicted_Output])
                self.MT_general.Full_Predicted_bucket[key] = pd.concat([self.MT_general.Full_Predicted_bucket[key], self.Comp_Model.Current_predicted_Output])

