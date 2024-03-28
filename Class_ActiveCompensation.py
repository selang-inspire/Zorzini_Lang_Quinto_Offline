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
    def __init__(self, Input, Error, MT_General, ModelFrequency, InfluxDB):
        #Initialization
        self.InfluxDBQuery = InfluxDB
        self.MT_general = MT_General #Access to global MT_data, link to it
        self.Comp_Model = None  # initialize the model
        self.Input_train = Input
        self.Error_train = Error
        self.first = True #First time normalization, to get the mean and std. dev. of the training data
        self.ModelFrequency = ModelFrequency


    def Save_TrainData(self):
        # save in Datamanager
        self.MT_general.Train_Input_bucket = self.Input_train
        self.MT_general.Train_Output_bucket = self.Error_train

    def Start_Compensation(self):
        self.MT_general.Full_Input_bucket = {key: pd.DataFrame() for key in self.Input_train.keys()}
        self.MT_general.Full_Predicted_bucket = {key: pd.DataFrame() for key in self.Input_train.keys()}
        self.MT_general.Predicted_bucket = {key: pd.DataFrame() for key in self.Input_train.keys()}

        for key in self.MT_general.Full_Input_bucket.keys():
            self.MT_general.Full_Input_bucket[key] = self.Input_train[key]
            self.MT_general.Full_Predicted_bucket[key] = self.Comp_Model.Model_TrainPredict(self.Error_train[key], key)
        #for step in range(100):
        self.get_actual_input()
        self.split_Inputs_to_dict()
        self.ModelStep()


    def get_actual_input(self):
        InputNames, time_res, results = self.InfluxDBQuery.query(start_iso=None, end_iso=None)
        #timestamp_swiss = time_res.astimezone(swiss_tz)
        self.Actual_Input_DF = self.MT_general.Table_Layout_Panda(time_res, InputNames, results)
        self.current_time = self.Actual_Input_DF['Time'].iloc[-1] #get actual time
        #self.Comp_Model.Current_Test_Input = self.MT_general.Test_Input_bucket

    def ModelStep(self):
        current_time = pd.to_datetime(self.current_time)
        # Add 30 seconds to the current time
        next_time = current_time + timedelta(seconds=self.ModelFrequency)
        # Wait until the next time is reached
        while next_time > datetime.now(): #wait until next measurement input reached
            pass  # wait
        print(next_time)
        print(datetime.now())

    def split_Inputs_to_dict(self):
        self.selected_input_test = {} #actual Input for each error
        if self.MT_general.Selected_Input_Names is not None:
            for key, columns in self.MT_general.Selected_Input_Names.items():
                self.selected_input_test[key] = self.Actual_Input_DF[columns]
        else:
            for key in self.MT_general.Full_Input_bucket.keys():
                self.selected_input_test[key] = self.Actual_Input_DF
        for key in self.MT_general.Full_Input_bucket.keys():
            self.MT_general.Predicted_bucket[key] = pd.concat([self.MT_general.Predicted_bucket[key], self.selected_input_test[key]])