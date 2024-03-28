import pandas as pd
from threading import Thread, Event
import csv
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.metrics import root_mean_squared_error
from statsmodels.tsa.api import ARDL
from statsmodels.tsa.api import ardl_select_order


#Model definition and use
class Model:
    def __init__(self):
        self.ModelType = [] #Different Model architectures
        #Input data for the model
        self.TrainData_Input = None #exogeneous training data for comp model
        self.TrainData_Output = None #endogenous training data for comp model
        #Dynamic Input Data for the model
        self.Current_and_previous_Input = None
        self.Current_Test_Input = None
        #Actual time value
        self.timestamp = None #Actual time of predicted value
        self.comp_wert = None #Which error is compensated
        #Output Data of the model
        self.Current_predicted_Output = None #pd.DataFrame({'Time': ['2024-03-10 00:00:00'],'Wert_1': [1], 'Wert_4': [0.0]})
        #Models for the compensation
        self.models = {} #contains the compensation models for each error in a dictionary
        self.models_fit = {} #contains the trained compensation model for each error in a dictionary

    def Generate(self):
        '''
        - The Model is generated here
        - Here the Model will be trained with the training data and is after ready for prediction
        '''
        print("=" * 100)
        # Iterate over the keys in the dictionaries
        for key in self.TrainData_Output.keys():
            # Preprocess training Data
            TrainData_Output = self.preprocess(self.TrainData_Output[key], False)
            TrainData_Input = self.preprocess(self.TrainData_Input[key], False)

            if self.ModelType == "ARDL":
                na = 2  # Order of the ARDL model
                nb = 2  # Lags of the ARDL model
                endog = TrainData_Output  # is a pd.DataFrame, endogeneous variables (Displacement)
                exog = TrainData_Input  # is a pd.DataFrame, Input variables (Temperature)
                model = ARDL(endog=endog, lags=nb, exog=exog, order=na, trend='c')
                model_fit = model.fit()
                # Store the model and its fitted version
                self.models[key] = model
                self.models_fit[key] = model_fit
                print(model_fit.summary())  # Prints the summary of the model as an overview
                print("ARDL Model for key {} is Initialized".format(key))
            elif self.ModelType == "FFNN":
                print("FFNN Model for key {} is Initialized".format(key))
                pass
            elif self.ModelType == "LSTM":
                print("LSTM Model for key {} is Initialized".format(key))
                pass
        print("=" * 100)

    def Model_TrainPredict(self, Error_train, key):
        '''
        - This function is used to predict the trained output of the model
        - The model need to be initialized before calling this function
        - This function is only used as a first step to predict the output of the training data
        '''
        #self.MT_general.Full_Input_bucket = self.Comp_Model.Model_TrainPredict(self.Error_train)
        error_df = Error_train.copy()
        #initialize for each Model
        TrainData_Input = self.preprocess(self.TrainData_Input[key], False)
        if self.ModelType == "ARDL":
            predictions = self.models_fit[key].predict(exog=TrainData_Input)
        #print(predictions)
        error_df['Wert_4'] = predictions
        print("-" * 100)
        return(error_df)

    def Pre_Model_ActivePredict(self):
        '''
        - This function is used to update the exogeneous data for the model
        - since measurements are taken at each timestep, the exogeneous data is updated at each timestep
        - The model need to be initialized before calling this function
        - This function should be called before Model_predict function
        '''
        exog_oos = self.preprocess(self.Current_Test_Input, True)
        self.Current_and_previous_Input = pd.concat([self.Current_and_previous_Input, exog_oos])
        self.exog = self.Current_and_previous_Input

    def Model_Predict(self, step, key): #TODO: Make model more efficient that RAM is not overloaded
        '''
        - This function is used to predict the output of the model
        - The model need to be initialized before calling this function
        - This function should be called in a for or while loop to predict the output for each timestep
        - step is the numerator of the for/while loop which should be inserted in this function
        '''
        if self.ModelType == "ARDL":
            predictions = self.models_fit[key].predict(start=len(self.TrainData_Output[key]), end=step+len(self.TrainData_Output[key]), exog_oos=self.exog)
        print(predictions)
        prediction = self.postprocess(predictions, key)
        self.Current_predicted_Output = prediction
        print("Current Prediction:")
        print(self.Current_predicted_Output)
        print("-" * 100)

    def preprocess(self, Data, stamps):
        '''
        This function preprocesses the data before it is used in the model
        - The data is converted to a float, else the model will not work
        - The time column is removed, as it is not used in the model, since the it should be columnwise the same timestep
        '''
        if stamps == None:
            stamps = False #True if the time column should be saved (for dynmaic), False for training
        #Preprocess the Data
        if 'Time' in Data.columns:
            if stamps == True:
                self.timestamp = pd.DataFrame(Data['Time'])
            Data = Data.drop(columns=['Time'])
        if 'Wert_1' in Data.columns:
            Data = Data.drop(columns=['Wert_1'])
        Data = Data.astype(float)
        return Data

    def postprocess(self, Data, key):
        '''
        This function postprocesses the data after it is used in the model
        - The data is converted to a DataFrame
        - The time column is added again
        - The data is saved in the correct format
        '''
        #Postprocess the Data
        error_number = int(key[-1])
        Data = pd.DataFrame(Data)
        Current_predicted_bucket = pd.DataFrame({'Time': ['0000-00-00 00:00:00'],'Wert_1': [None], 'Wert_4': [0.0]})
        Current_predicted_bucket.iloc[0,0] = self.timestamp.iloc[0,0]
        Current_predicted_bucket.iloc[0,1] = error_number
        Current_predicted_bucket.iloc[0,2] = Data.iloc[-1,0] #Predicted Value. [-1, 0] war vorher
        Current_predicted_bucket.set_index(self.timestamp.index, inplace=True)
        return Current_predicted_bucket

    def RMSE_Calculation_OFFLINE(self, MT_General_data):
        '''
        This function is used to calculate the Root Mean Squared Error
        - The RMSE is calculated for the training and test data
        - The RMSE is calculated for the compensated and uncompensated data
        '''
        self.MT_data = MT_General_data
        Data = self.MT_data.Test_Output_bucket.copy()
        for key in Data.keys():
            Data[key].reset_index(drop=True, inplace=True)
            Data[key] = Data[key].drop(columns=['Time'])
            Data[key] = Data[key].drop(columns=['Wert_1'])

        self.MT_data.Comp_RMSE = {key: None for key in Data}
        self.MT_data.Uncomp_RMSE = {key: None for key in Data}
        self.MT_data.Total_reduced_RMSE = {key: None for key in Data}

        # Calculate the root mean squared error (RMSE) for each key in the dictionary
        for key in Data.keys():
            Predictions = self.MT_data.Predicted_bucket[key]
            Predictions = Predictions.drop(columns=['Time'])
            Predictions = Predictions.drop(columns=['Wert_1'])
            zero_line = [0] * (len(Data[key]))
            self.MT_data.Comp_RMSE[key] = root_mean_squared_error(Data[key], Predictions.dropna())
            self.MT_data.Uncomp_RMSE[key] = root_mean_squared_error(zero_line, Data[key])
            self.MT_data.Total_reduced_RMSE[key] = 1 - self.MT_data.Comp_RMSE[key] / self.MT_data.Uncomp_RMSE[key]

            # Print the results
            print("=" * 100)
            print(f'Comp RMSE for {key}: {self.MT_data.Comp_RMSE[key]}')
            print(f'Uncomp RMSE for {key}: {self.MT_data.Uncomp_RMSE[key]}')
            print('-' * 100)
            print(f'Total reduced RMSE for {key}: {self.MT_data.Total_reduced_RMSE[key]}')
            print("=" * 100)

    def plot_comp_results_OFFLINE(self, MT_data):
        '''
        This function is used to plot the results of the compensation model
        - This function calls the Datamanager (General Machine Data) to get the data
        - This function only works for OFFLINE Simulation environment
        - up to 21 different colors are available, so only 21 different errors can be plotted if multicolor_allowed is True
        '''
        multicolor_allowed = True
        self.MT_data = MT_data
        colors_list = ['red', 'green', 'blue', 'cyan', 'magenta', 'yellow', 'orange', 'purple', 'pink', 'brown',
                       'black', 'teal', 'coral', 'lightblue', 'lime', 'lavender', 'turquoise', 'darkgreen', 'tan',
                       'salmon', 'gold']

        # Iterate over the keys in the dictionaries
        for idx, key in enumerate(self.MT_data.Full_Predicted_bucket.keys()):
            predictions = self.MT_data.Full_Predicted_bucket[key]
            temp_data = self.MT_data.Full_Input_bucket[key]
            X = pd.concat([self.MT_data.Train_Output_bucket[key], self.MT_data.Test_Output_bucket[key]])
            X.reset_index(drop=True, inplace=True)  # because self.MT_data.Train_Output_bucket starts at index 0, else wont recognize it
            train_data = self.MT_data.Train_Output_bucket[key]
            direction = self.MT_data.Full_Predicted_bucket[key]['Wert_1'].iloc[-1]
            reduced_thermal_error = self.MT_data.Total_reduced_RMSE[key]
            train_data = self.MT_data.convert_time_to_seconds(train_data)
            temp_data = self.MT_data.convert_time_to_seconds(temp_data)
            X = self.MT_data.convert_time_to_seconds(X)
            training_end = train_data['Time'].iloc[-1]

            # Plotting
            fig, axs = plt.subplots(3, 1, figsize=(19, 10))

            colors = colors_list[idx % len(colors_list)] if multicolor_allowed else 'red'
            #if direction == 'E_Y':
            #    colors = 'green'
            #if direction == 'E_Z':
            #    colors = 'blue'
            #if direction == 'E_X':
            #    colors = 'red'
            #else:
            #    colors = 'red'

            # Plot 1: Displacement and Predicted Displacement
            axs[0].plot(X['Time'] / 3600, X.iloc[:, 2:], label=f'Measured {key}', color=colors)
            axs[0].plot(X['Time'] / 3600, predictions.iloc[:, 2:], label=f'Predicted {key}', linestyle='--', color=colors)
            axs[0].axvline(training_end / 3600, color='black', label='Training End', linestyle='-')
            axs[0].set_title(f'Compensation Model {self.ModelType} {key} {reduced_thermal_error}', fontsize=16)
            axs[0].set_xlabel('Time [h]', fontsize=16)
            axs[0].set_ylabel('Displacement [μm]', fontsize=16)
            axs[0].tick_params(axis='both', labelsize=16)
            axs[0].legend(loc='upper center', ncol=3, fontsize=12)

            residuals = X.iloc[:, 2:] - predictions.iloc[:, 2:]
            # predictions = pd.concat([predictions], axis=0)
            residuals = pd.concat([residuals], axis=0)

            # Plot 2: Residuals
            axs[1].plot(X['Time'] / 3600, residuals, color=colors)
            axs[1].legend(['Residual'], loc='upper right', fontsize=12)
            axs[1].set_xlabel('Time [h]', fontsize=16)
            axs[1].set_ylabel('Residual [μm]', fontsize=16)
            axs[1].set_title(f'Residual error compensation model {key}', fontsize=16)
            axs[1].tick_params(axis='both', labelsize=16)
            axs[1].axvline(training_end / 3600, color='black', linestyle='-')

            # Plot 3: Temperature
            for column in temp_data.columns[1:]:
                axs[2].plot(temp_data['Time'] / 3600, temp_data[column], label=column)

            axs[2].set_xlabel('Time [h]', fontsize=16)
            axs[2].set_ylabel('Temperature [°C]', fontsize=16)
            axs[2].set_title(f'Model Inputs', fontsize=16)
            axs[2].tick_params(axis='both', labelsize=16)
            axs[2].legend(loc='upper center', ncol=6)
            axs[2].axvline(training_end / 3600, color='black', linestyle='-')

            for ax in axs:
                ax.grid(True)

            plt.tight_layout()
            plt.show()



