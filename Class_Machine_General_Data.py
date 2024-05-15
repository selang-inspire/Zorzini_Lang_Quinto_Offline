'''
Author: Mario Zorzini (mzorzini)
Date: 2024-03-12
'''

import pandas as pd
import datetime
import numpy as np
import sys
from pytz import timezone


class Machine_Data:
    '''
    - This Class is the only class that is used for a standardized data exchange
    '''
    def __init__(self):
        '''
        - The data is stored in the class and can be accessed by the other classes
        - Here is the storage of the data
        - Additional data can be added here
        '''
        ############Error_Data################
        self.Global_Error_Time = None #Time of raw error data
        self.Error_Number_order = None #Error number order
        self.Error_Measurements = None #Raw error data
        ##########Reference_Error_Data########
        self.Reference_Error = None #This includes a dataframe with the reference error data, the Time and the reference error are listed here
        self.Reference_Input = None #This includes a dataframe with the reference input data, the Time and the reference input are listed here
        #############Temp_Data################
        self.Input_Sensornames = None #Sensor/Input source names
        self.Global_Meas_Time_Temp = None #Time of raw Input data
        self.Temp_Values = None #Raw Input data
        self.Sampled_InputData = None #Sampled Input data, Disctionary contains each Input dataset sampled according to the error
        ############Raw_Inhternal_Data########
        self.Raw_Energy_Data = None #Raw Internal Data
        self.Raw_Power_Data = None #Raw Internal Data
        self.Raw_Indigenous_Temperature_Data = None #Raw Internal Data
        #############Processed Data##########
        self.processed_Energy_Data = None #Processed Internal Data
        self.processed_indigenous_temperature_data = None #Processed Internal Data
        self.processed_Power_Data = None #Processed Internal Data
        self.processed_Power_withoutSmoothedEnergy = None #Energy to Power Data without smoothing energy
        #############z-score normalization###
        self.normalization_mean = None #mean of the training data
        self.normalization_std = None #std. dev. of the training data
        ############Comp_Model_Values#########
        #Input Selection
        self.SelectedInputs_Train = None #Selected Inputs for the model
        self.Selected_Input_Names = None #Selected Inputs Names evaluated by Input Selection
        #static values in dictionaries
        self.Train_Input_bucket = None #static values, for training phase of the comp. model
        self.Train_Output_bucket = None #static values, for training phase of the comp. model
        self.Test_Output_bucket = None #static error test values, only for simulation or measurement during the test phase
        self.Test_Original_Input_bucket = None #static test values,
        #dynamic values
        self.Test_Input_bucket = None #dynamic test values, updated after each timestep
        self.Predicted_bucket = None #will save/record predicted output data (Error) for later use after simulation
        self.Full_Input_bucket = None #will save/record all input data for later use after simulation
        self.Full_Predicted_bucket = None #will save/record all output data (Error) for later use after simulation
        #RMSE_Values
        self.Comp_RMSE = None #RMSE of the compensated data
        self.Uncomp_RMSE = None #RMSE of the uncompensated data
        self.Total_reduced_RMSE = None #Total reduced RMSE
        #PADDING Row Indices
        self.Padding_Row_Indices = None #Time values for the padding of the data
        self.time_jump_indices = None #Time jump Row indices
        #InputData before sampling to Error Data
        self.orig_InputData = None #Original Input Data before sampling to Error Data

    def error_data(self, data1, data2, data3):
        '''
        - This def will be used to load the error data from the excel file and store the Original data
        '''
        self.Global_Error_Time = data1
        self.Error_Number_order = data2
        self.Error_Measurements = data3

    def temp_data(self, data1, data2, time_res_energy, data3):
        '''
        - This def will be used to load the temperature data from the InfluxDB and store the Original data
        '''
        self.Input_Sensornames = data1
        self.Global_Meas_Time_Temp = data2
        self.Global_Meas_Time_Energy = time_res_energy
        self.Temp_Values = data3

    def get_error_data(self):
        '''
        - This def will be used to get the error data from the class
        '''
        return self.Global_Error_Time, self.Error_Number_order, self.Error_Measurements

    def get_temp_data(self):
        '''
        - This def will be used to get the temperature data from the class
        '''
        return self.Input_Sensornames, self.Global_Meas_Time_Temp, self.Temp_Values

    def Table_Layout_Panda(self, Global_Meas_Time_Temp, Input_Sensornames, Temp_Values):
        '''
        - Table_Layout_Panda(self, Time, Column Names, Values)
        - This def will make a nice temperature dataframe layout from the InfluxDB data
        - The format is important for the further processing
        - The Output is a panda dataframe
        '''
        # Temp Data
        dataFrame = pd.DataFrame(Temp_Values)
        Temp_data = dataFrame.transpose()
        Temp_data.rename(columns=dict(zip(Temp_data.columns, Input_Sensornames)), inplace=True)
        datetime_values = [t[1] for t in Global_Meas_Time_Temp if t[0] == 'temperature']
        swiss_tz = timezone('Europe/Zurich') #UTC conversion
        timestamps_swiss = [timestamp.astimezone(swiss_tz) for timestamp in datetime_values] #UTC conversion
        time_column = pd.Series(timestamps_swiss) #UTC conversion
        Temp_data.insert(loc=0, column='Time', value=time_column)
        Temp_data['Time'] = pd.to_datetime(Temp_data['Time']).dt.strftime('%Y-%m-%d %H:%M:%S.%f').str[:-3]
        return Temp_data

    #Interpolation
    def sample_dataframe(self, df, timestamps):
        """
        Sample a Pandas DataFrame based on specified timestamps.
        Use case:
        - Sample temperature data at the same timestamps as the error data.
        Parameters:
        - df: Pandas DataFrame to be sampled.
        - timestamps: List of timestamps to sample the DataFrame.
        Returns:
        - Sampled DataFrame at the specified timestamps.
        interpolation_method:
        - 'linear', 'backfill', 'ffill', 'nearest', 'polynomial', 'spline', 'akima', 'cubicspline', 'time'
        """
        df['Time'] = pd.to_datetime(df['Time']) #Maybe not necessary?
        df = df.drop_duplicates(subset=['Time']) #wegen doppelten Einträgen
        # Set 'Time' column as index
        df.set_index('Time', inplace=True)
        # Select rows based on the closest timestamps available
        timestamps = [pd.Timestamp(t) for t in timestamps]
        sampled_df = df.reindex(df.index.union(timestamps))
        sampled_df = sampled_df.interpolate(method='linear')
        sampled_df = sampled_df.reindex(timestamps)
        # Reset index to make 'Time' a column again
        sampled_df.reset_index(inplace=True)
        return sampled_df


    #z-score normalization
    def z_score_normalization(self, dataframe, first):
        '''
        - Z-Score normalization
        - The order of the Code here is important, else the normalization will not work
        - The first time normalization, to get the mean and std. dev. of the training data
        - The mean and std. dev. of the training data is used for the normalization of the test data
        '''
        # Z-Score normalization
        Wert = None
        Timecolumn = None

        if 'Time' in dataframe.columns:
            Timecolumn = dataframe['Time']
            dataframe = dataframe.drop(columns=['Time'])
        if 'Wert_1' in dataframe.columns:
            Wert = dataframe['Wert_1']
            dataframe = dataframe.drop(columns=['Wert_1'])
        if first==True:
            self.normalization_mean = dataframe.mean()
            self.normalization_std = dataframe.std()
            dataframe = (dataframe - self.normalization_mean) / self.normalization_std
        else:
            dataframe = (dataframe - self.normalization_mean) / self.normalization_std

        if Wert is not None:
            dataframe.insert(0, 'Wert_1', Wert)
        if Timecolumn is not None:
            dataframe.insert(0, 'Time', Timecolumn)

        return dataframe

    def convert_time_to_seconds(self, df):
        '''
        - Convert time to seconds
        - This is primarily used for Plotting the Results
        '''
        df_copy = df.copy() #copy, else it wil overwrite the original dataframe
        df_copy['Time'] = pd.to_datetime(df_copy['Time'])
        reference_time = df_copy['Time'].min() #reference time, smallest time resp. should be the first timestamp
        df_copy['Time'] = (df_copy['Time'] - reference_time).dt.total_seconds().round(3) #rounded to 3 decimal places
        return df_copy
