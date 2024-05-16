import pandas as pd
from threading import Thread, Event
import csv
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.metrics import root_mean_squared_error
#from statsmodels.tsa.api import ARDL
#from statsmodels.tsa.api import ardl_select_order
import os
import pickle
from statsmodels.tsa.tsatools import lagmat
from typing import Optional, Callable
from Class_ARX_Model import ARDL
from Class_ARX_Model import ardl_select_order
from numpy.typing import ArrayLike#Model definition and use
class Model:
    def __init__(self):
        self.MT_data = None  # General Machine Data
        self.ONLINE = False  # True if the model is used in ONLINE mode, False if the model is used in OFFLINE mode
        self.ModelType = []  # Different Model architectures
        # Input data for the model
        self.TrainData_Input = None  # exogeneous training data for comp model
        self.TrainData_Output = None  # endogenous training data for comp model
        # Dynamic Input Data for the model
        self.Current_and_previous_Input = None
        self.Current_Test_Input = None
        # Actual time value
        self.timestamp = None  # Actual time of predicted value
        self.comp_wert = None  # Which error is compensated
        # Previous Data before actual Online prediction
        self.Previous_Input_beforeONLINECompensation = None
        # Output Data of the model
        self.Current_predicted_Output = None  # pd.DataFrame({'Time': ['2024-03-10 00:00:00'],'Wert_1': [1], 'Wert_4': [0.0]})
        # Models for the compensation
        self.models = {}  # contains the compensation models for each error in a dictionary
        self.models_fit = {}  # contains the trained compensation model for each error in a dictionary
        # If TempSensors are used
        self.TempSensors = False
        # Model Directory where the models are saved
        self.model_directory = None
        # Padding Time
        self.PADDING_Timestamp = None  # List of Timestamps where padding should occur
        # if Padding
        self.PAD = None  # True if padding is necessary
        # All Input Data before sampling according to Error Data
        self.Original_InputData = None  # Original Input Data before sampling to Error Data (only for OFFLINE)
        # Timestamp of the current prediction OFFLINE
        self.Timestamp = None  # Timestamp of the current prediction
        # save or load a model
        self.save_load_model = None


    def Generate(self):
        '''
        - The Model is generated here
        - Here the Model will be trained with the training data and is after ready for prediction
        '''
        print("=" * 100)
        print("Model Generation/Loading Started")
        print("-" * 100)
        self.Current_and_previous_Input_2 = {key: None for key in self.TrainData_Output.keys()}
        # Iterate over the keys in the dictionaries
        for key in self.TrainData_Output.keys():
            # Call the save_or_load_model function
            self.save_or_load_model(key)
        print("-" * 100)
        print("Model Generation/Loading Finished")
        print("=" * 100)

    def save_or_load_model(self, key):
        model_file = os.path.join(self.model_directory, f'{key}_model.pkl')
        model_file_Inputs = os.path.join(self.model_directory, f'{key}_model_Inputs.pkl')
        model_save = self.save_load_model #set true if a model should be read in or saved, it only saves a model if no previous available

        # Check if the model file exists
        if os.path.exists(model_file) and model_save:
            # Load the model from the file
            with open(model_file, 'rb') as file:
                self.models_fit[key] = pickle.load(file)
                print(f"Loaded model for key {key} from {model_file}")

            with open(model_file_Inputs, 'rb') as file:
                self.MT_data.Selected_Input_Names[key] = pickle.load(file)
                print(f"Loaded selected feature names for key {key} from {model_file_Inputs}")
                print(f"Selected feature names for key {key}: {self.MT_data.Selected_Input_Names[key]}")
                print("-" * 100)

        else:
            if self.ModelType == "ARX":
                na = 2  # Order of the ARX model
                nb = 2  # Lags of the ARX model
                endog = self.preprocess(self.TrainData_Output[key],False)  # is a pd.DataFrame, endogeneous variables (Displacement)
                exog = self.preprocess(self.TrainData_Input[key],False)  # is a pd.DataFrame, Input variables (Temperature)

                model = ARDL(endog=endog, lags=nb, exog=exog, order=na, trend='c')

                ListIndicesToInsertNaN = self.MT_data.time_jump_indices[key]
                lastRowIndices = endog.index[-1]
                filtered_list = [i for i in ListIndicesToInsertNaN if i <= lastRowIndices]
                # endog.iloc[filtered_list, :] = np.nan
                # filtered_list = list(range(1, 401))
                model.indicesForWeightZero = filtered_list

                model_fit = model.fit()
                # Store the model and its fitted version
                self.models[key] = model
                self.models_fit[key] = model_fit
                print(model_fit.summary())  # Prints the summary of the model as an overview

            if self.ModelType == "AIC":
                # Preprocess training Data
                endog = self.preprocess(self.TrainData_Output[key],False)  # is a pd.DataFrame, endogeneous variables (Displacement)
                exog = self.preprocess(self.TrainData_Input[key],False)  # is a pd.DataFrame, Input variables (Temperature)
                maxlag = 5  # maximum lag order to consider for endogenous variables
                maxorder = 5  # maximum lag order to consider for exogenous variables
                # Select the optimal order of the ARDL model based on AIC
                order_selection = ardl_select_order(endog, maxlag, exog, maxorder, trend='c', ic='aic')  # akaike information criterion to select order and lags
                model = order_selection.model  # ARDL(endog=endog, lags=nb, exog=exog, order=na, trend='c')

                #Insert Indices were weights should be set to zero
                ListIndicesToInsertNaN = self.MT_data.time_jump_indices[key]
                lastRowIndices = endog.index[-1]
                filtered_list = [i for i in ListIndicesToInsertNaN if i <= lastRowIndices]
                model.indicesForWeightZero = filtered_list

                model_fit = model.fit()
                # Store the model and its fitted version
                self.models[key] = model
                self.models_fit[key] = model_fit
                print(model_fit.summary())  # Prints the summary of the model as an overview
                print("ARX Model for key {} is Initialized".format(key))

            if self.ModelType == "FFNN":
                print("FFNN Model for key {} is Initialized".format(key))
                pass
            if self.ModelType == "LSTM":
                print("LSTM Model for key {} is Initialized".format(key))
                pass

            # Save the model to the file
            if model_save:
                with open(model_file, 'wb') as file:
                    pickle.dump(self.models_fit[key], file)
                    print(f"Saved model for key {key} to {model_file}")

                with open(model_file_Inputs, 'wb') as file:
                    if self.MT_data.Selected_Input_Names is not None:
                        pickle.dump(pickle.dump(self.MT_data.Selected_Input_Names[key], file), file)
                        print(f"Saved selected feature names for key {key} to {model_file_Inputs}")

    def Model_TrainPredict(self, Error_train, key):
        '''
        - This function is used to predict the trained output of the model
        - The model need to be initialized before calling this function
        - This function is only used as a first step to predict the output of the training data
        '''
        # self.MT_general.Full_Input_bucket = self.Comp_Model.Model_TrainPredict(self.Error_train)
        error_df = Error_train.copy()
        # initialize for each Model
        #TrainData_Input = self.preprocess(self.TrainData_Input[key], False)
        # for i in range(len(TrainData_Input)):
        #    actual_input = pd.DataFrame(TrainData_Input.iloc[:i+1])
        if self.ModelType == "ARX":
            predictions = self.models_fit[key].predict()

            # Delete the values which were weighted as zero in trained model
            ListIndicesToInsertNaN = self.MT_data.time_jump_indices[key]
            lastRowIndices = error_df.index[-1]
            filtered_list = [i for i in ListIndicesToInsertNaN if i <= lastRowIndices]
            max_lag = max(max(value) for value in self.models_fit[key].model._order.values())
            for pos in filtered_list:
                j = 0
                while j < max_lag:
                    predictions.iloc[pos + j] = np.nan
                    j += 1
        #predictions.iloc[filtered_list] = np.nan
        # print(predictions)
        error_df['Wert_4'] = predictions
        print("-" * 100)
        return (error_df)

    def Pre_Model_ActivePredict(
            self):  # TODO: This function was the old Pre_model_ActivePredict. The new one is called: Pre_Model_ActivePredict_2. This one remains for educational purposes. Delete this function, Pre_Model_ActivePrdict_2 is bettr and more robust, maybe not necessary this function generally?
        '''
        - This function is used to update the exogeneous data for the model
        - since measurements are taken at each timestep, the exogeneous data is updated at each timestep
        - The model need to be initialized before calling this function
        - This function should be called before Model_predict function
        '''
        exog_oos = self.preprocess(self.Current_Test_Input, True)
        self.Current_and_previous_Input = pd.concat([self.Current_and_previous_Input, exog_oos])
        self.exog = self.Current_and_previous_Input
        print(self.exog)

    def Pre_Model_ActivePredict_2(self, key):  # Pre_Model_ActivePredict_2 is better and more robust
        '''
        - This function is used to update the exogeneous data for the model
        - since measurements are taken at each timestep, the exogeneous data is updated at each timestep
        - The model need to be initialized before calling this function
        - This function should be called before Model_predict function
        '''
        #print(self.Current_Test_Input)
        exog_oos = self.preprocess(self.Current_Test_Input, True)
        # if self.Current_and_previous_Input_2[key] is not None and len(self.Current_and_previous_Input_2[key]) > 5: #TODO: keep only necessary data to not overun RAM
        #    # Drop the first few rows but keep the last nb+1 rows
        #    self.Current_and_previous_Input_2[key] = self.Current_and_previous_Input_2[key].drop(self.Current_and_previous_Input_2[key].index[:-5 - 1])
        if self.ONLINE == False:
            self.PADDING_Timestamp = self.MT_data.Padding_Row_Indices[key]  # List of timetsamps where PADDING should occur
            if self.Current_Test_Input['Time'].iloc[0] in self.PADDING_Timestamp:
                self.PAD[key] = True
                self.Current_and_previous_Input_2[key] = None
                self.Timestamp = self.Current_Test_Input['Time'].iloc[0]
                self.Timestamp = self.Timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')
            if self.TempSensors and self.Timestamp != None:
                self.Previous_Input_beforeONLINECompensation = self.Original_InputData[self.Timestamp]
        self.Current_and_previous_Input_2[key] = pd.concat([self.Current_and_previous_Input_2[key], exog_oos])
        self.Current_and_previous_Input_2[key].reset_index(drop=True, inplace=True)  # Not necessary
        self.exog = self.Current_and_previous_Input_2[key]
        # print(self.exog) #for debugging

    def Model_Predict(self, step, key):  # TODO: Make model more efficient that RAM is not overloaded
        '''
        - This function is used to predict the output of the model
        - The model need to be initialized before calling this function
        - This function should be called in a for or while loop to predict the output for each timestep
        - step is the numerator of the for/while loop which should be inserted in this function
        '''
        PADDING = False
        if self.ONLINE:
            PADDING = True

        if self.ONLINE == False:
            if self.PAD[key]:
                PADDING = True

        if self.ModelType == "ARX":
            # predictions = self.models_fit[key].predict(start=len(self.TrainData_Output[key]), end=step+len(self.TrainData_Output[key]), exog_oos=self.exog) #Maybe dynamic=True?
            predictions = self.Dynamic_predict(PADDING,
                                       params=self.models_fit[key].params,
                                       start=len(self.models_fit[key].data.orig_exog),
                                       # start=len(self.TrainData_Output[key]),
                                       end=len(self.exog)-1 + len(self.models_fit[key].data.orig_exog),
                                       # end=step+len(self.TrainData_Output[key]),
                                       dynamic=False,
                                       exog=None,
                                       exog_oos=self.exog,
                                       fixed=None,
                                       fixed_oos=None,
                                       data=self.models_fit[key].model.data,
                                       orig_exog=self.models_fit[key].model.data.orig_exog,
                                       _fixed=self.models_fit[key].model._fixed,
                                       _causal=self.models_fit[key].model._causal,
                                       _lags=self.models_fit[key].model._lags,
                                       _order=self.models_fit[key].model._order,
                                       _hold_back=self.models_fit[key].model._hold_back,
                                       endog=self.models_fit[key].model.endog,
                                       _deterministic_reg=self.models_fit[key].model._deterministic_reg,
                                       _wrap_prediction=self.models_fit[key].model._wrap_prediction,
                                       _prepare_prediction=self.models_fit[key].model._prepare_prediction,
                                       _forecasting_x=self.models_fit[key].model._forecasting_x,
                                       _parse_dynamic=self.models_fit[key].model._parse_dynamic,
                                       _x=self.models_fit[key].model._x,
                                       _format_exog=self.models_fit[key].model._format_exog
                                       )
        # print(predictions) #for debugging
        prediction = self.postprocess(predictions, key, step)
        self.Current_predicted_Output = prediction
        print("Current Prediction:")
        print(self.Current_predicted_Output)
        print("-" * 100)

    def check_exog(self, arr, name, orig, exact):
        '''
        - Check the exogenous variables for the in-sample and out-of-sample data
        - Is used in Dynamic_predict function as a check mechanism
        '''
        if isinstance(orig, pd.DataFrame):
            if not isinstance(arr, pd.DataFrame):
                raise TypeError(f"{name} must be a DataFrame when the original exog was a DataFrame")
            if sorted(arr.columns) != sorted(orig.columns):
                raise ValueError(f"{name} must have the same columns as the original exog")
        else:
            arr = np.asarray(arr)
        if arr.ndim != 2 or arr.shape[1] != orig.shape[1]:
            raise ValueError(f"{name} must have the same number of columns as the original data, {orig.shape[1]}")
        if exact and arr.shape[0] != orig.shape[0]:
            raise ValueError(f"{name} must have the same number of rows as the original data.")
        return arr

    def Dynamic_predict(self, PADDING, params, start=None, end=None, dynamic=False, exog=None, exog_oos=None, fixed=None,
                fixed_oos=None,
                data=None, orig_exog=None, _fixed=None, _causal=None, _lags=None, _order=None, _hold_back=None,
                endog=None,
                _deterministic_reg=None, _wrap_prediction=None, _prepare_prediction=None, _forecasting_x=None,
                _parse_dynamic=None, _x=None,
                _format_exog=None):
        '''
        - This function is used to predict the dynamic output of the model
        - The model need to be initialized before calling this function
        - This function is only valid for ARX models!
        - Since we have Autoregressive consideration this function manages the Time Gaps by implementig PADDING
        '''
        # Prepare the prediction by getting the parameters, exogenous variables, start and end points

        params, exog, exog_oos, start, end, num_oos = _prepare_prediction(params, exog, exog_oos, start, end)

        # Check the exogenous variables for the in-sample and out-of-sample data
        exog = self.check_exog(exog, "exog", orig_exog, True) if exog is not None else None
        exog_oos = self.check_exog(exog_oos, "exog_oos", orig_exog, False) if exog_oos is not None else None

        # Check the fixed variables for the in-sample and out-of-sample data
        fixed = self.check_exog(fixed, "fixed", _fixed, True) if fixed is not None else None
        fixed_oos = self.check_exog(np.asarray(fixed_oos), "fixed_oos", _fixed,
                                    False) if fixed_oos is not None else None

        # Determine the maximum one-step ahead forecast
        max_1step = 0 if _fixed.shape[1] or not _causal else np.inf if not _lags else min(_lags)
        if _order:
            min_exog = min([min(v) for v in _order.values()])
            max_1step = min(max_1step, min_exog)

        # Check if the number of out-of-sample observations is greater than the maximum one-step ahead forecast
        if num_oos > max_1step:
            if _order and exog_oos is None:
                raise ValueError(
                    "exog_oos must be provided when out-of-sample observations require values of the exog not in the original sample")
            elif _order and (exog_oos.shape[0] + max_1step) < num_oos:
                raise ValueError(
                    f"exog_oos must have at least {num_oos - max_1step} observations to produce {num_oos} forecasts based on the model specification.")
            if _fixed.shape[1] and fixed_oos is None:
                raise ValueError("fixed_oos must be provided when predicting out-of-sample observations")
            elif _fixed.shape[1] and fixed_oos.shape[0] < num_oos:
                raise ValueError(f"fixed_oos must have at least {num_oos} observations to produce {num_oos} forecasts.")

        # If exogenous variables are provided but not for out-of-sample, create a DataFrame with NaN values
        if exog is not None and exog_oos is None and num_oos:
            exog_oos = pd.DataFrame(np.full((num_oos, exog.shape[1]), np.nan), columns=orig_exog.columns) if isinstance(
                orig_exog, pd.DataFrame) else None

        x = _forecasting_x(start, end, num_oos, exog, exog_oos, fixed, fixed_oos)

        # Determine the start of the dynamic forecast
        dynamic_start = end + 1 - start if dynamic is False else _parse_dynamic(dynamic, start)
        if start < _hold_back:
            dynamic_start = max(dynamic_start, _hold_back - start)

        # Initialize the forecasts with NaN values
        fcasts = np.full(x.shape[0], np.nan)
        # Compute the one-step ahead forecasts
        fcasts[:dynamic_start] = x[:dynamic_start] @ params
        # Get the offset for the deterministic regressors
        offset = _deterministic_reg.shape[1]

        if PADDING:
            max_lag = max(max(value) for value in _order.values())
            exog_padded = orig_exog.copy()
            # Assume exog_padded is your DataFrame
            num_columns = exog_padded.shape[1]  # Get the number of columns in exog_padded
            zero_rows = pd.DataFrame(np.zeros((max_lag, num_columns)), columns=exog_padded.columns)  # Create a new DataFrame with two rows filled with zeros
            #Insert previous Temp meas before compensation started (only for Temp Sensors available)
            if self.TempSensors:  # insert previous Temp measurements before compensation started (only for Temp Sensors available)
                Previous_Comp_TempData = self.Previous_Input_beforeONLINECompensation.iloc[-max_lag:]  # Get the last rows of exog_padded
                Previous_Comp_TempData = Previous_Comp_TempData.drop(columns=['Time'])
                Previous_Comp_TempData.reset_index(drop=True, inplace=True)
                zero_rows.update(Previous_Comp_TempData)
            # Replace the last two rows of exog_padded with zero_rows
            exog_padded.iloc[-max_lag:] = zero_rows.values
            # Get the matrix for forecasting
            x = _forecasting_x(start, end, num_oos, exog_padded, exog_oos, fixed, fixed_oos)

        # Compute the dynamic forecasts
        for i in range(dynamic_start, fcasts.shape[0]):
            for j, lag in enumerate(_lags):
                loc = i - lag
                if PADDING:
                    val = fcasts[loc] if loc >= dynamic_start else 0
                else:
                    val = fcasts[loc] if loc >= dynamic_start else endog[start + loc]
                x[i, offset + j] = val
            fcasts[i] = x[i] @ params
        # Return the forecasts wrapped in the appropriate format
        return _wrap_prediction(fcasts, start, end + 1 + num_oos, 0)


    def preprocess(self, Data, stamps):
        '''
        This function preprocesses the data before it is used in the model
        - The data is converted to a float, else the model will not work
        - The time column is removed, as it is not used in the model, since the it should be columnwise the same timestep
        '''
        if stamps == None:
            stamps = False  # True if the time column should be saved (for dynamic), False for training
        # Preprocess the Data
        if 'Time' in Data.columns:
            if stamps == True:
                self.timestamp = pd.DataFrame(Data['Time'])
            #Data.set_index('Time', inplace=True)
            Data = Data.drop(columns=['Time'])
        if 'Wert_1' in Data.columns:
            Data = Data.drop(columns=['Wert_1'])
        Data = Data.astype(float)
        return Data

    def postprocess(self, Data, key, step):
        '''
        This function postprocesses the data after it is used in the model
        - The data is converted to a DataFrame
        - The time column is added again
        - The data is saved in the correct format
        '''
        # Postprocess the Data
        #error_number = int(key[-1]) #old version uses the error number since we hade 8 measurements for the displacements--> works now for grafana
        error_number = key
        Data = pd.DataFrame(Data)
        Current_predicted_bucket = pd.DataFrame({'Time': ['0000-00-00 00:00:00'], 'Wert_1': [None], 'Wert_4': [0.0]})
        Current_predicted_bucket.iloc[0, 0] = self.timestamp.iloc[0, 0]
        Current_predicted_bucket.iloc[0, 1] = error_number
        Current_predicted_bucket.iloc[0, 2] = Data.iloc[-1, 0]  # Predicted Value. [-1, 0] war vorher
        if self.ONLINE:
            Current_predicted_bucket.index = [step]
        else:
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
                       'salmon', 'gold', 'skyblue', 'olive']

        color_dict = {
            'X0B': 'red',
            'Y0B': 'green',
            'Z0B': 'blue',
            'X0C': 'darkred',
            'Y0C': 'darkgreen',
            'A0B': 'red',
            'C0B': 'blue',
            'B0B': 'green',
            'A0C': 'darkred',
            'C0C': 'darkblue',
            'B0C': 'darkgreen',
            'X0X': 'red',
            'Y0Y': 'green',
            'Z0Z': 'blue',
            'Y0X': 'green',
            'Z0X': 'blue',
            'A0X': 'red',
            'C0X': 'blue',
            'B0X': 'green',
            'A0Y': 'red',
            'C0Y': 'blue',
            'B0Y': 'green',
            'A0Z': 'red',
            'C0Z': 'blue',
            'B0Z': 'green',
            'X0Y': 'red',
            'X0Z': 'red',
            'Y0Z': 'green',
            'X0A': 'red',
            'Y0A': 'green',
            'Z0A': 'blue',
            'A0A': 'red',
            'C0A': 'blue',
            'B0A': 'green'
        }

        colors_list_input = ['orange', 'cyan', 'magenta', 'yellow', 'red', 'green', 'blue', 'purple', 'pink', 'brown',
                             'black', 'teal', 'coral', 'lightblue', 'lime', 'lavender', 'turquoise', 'darkgreen', 'tan',
                             'salmon', 'gold', 'skyblue', 'olive', 'indigo', 'maroon', 'navy', 'khaki', 'ivory',
                             'silver', 'plum', 'orchid', 'beige', 'sienna', 'tomato', 'bisque', 'slateblue',
                             'yellowgreen',
                             'seagreen', 'palegreen', 'peachpuff', 'linen']

        # Iterate over the keys in the dictionaries
        i = 0
        for idx, key in enumerate(self.MT_data.Full_Predicted_bucket.keys()):
            predictions = self.MT_data.Full_Predicted_bucket[key]
            temp_data = self.MT_data.Full_Input_bucket[key]
            X = pd.concat([self.MT_data.Train_Output_bucket[key], self.MT_data.Test_Output_bucket[key]])
            X.reset_index(drop=True,
                          inplace=True)  # because self.MT_data.Train_Output_bucket starts at index 0, else wont recognize it
            train_data = self.MT_data.Train_Output_bucket[key]
            direction = self.MT_data.Full_Predicted_bucket[key]['Wert_1'].iloc[-1]
            reduced_thermal_error = self.MT_data.Total_reduced_RMSE[key]
            train_data = self.MT_data.convert_time_to_seconds(train_data)
            temp_data = self.MT_data.convert_time_to_seconds(temp_data)
            X = self.MT_data.convert_time_to_seconds(X)
            #######################################################################################
            # Shift the times to close the gaps
            #######################################################################################
            # Ensure that 'Time' column is in datetime format
            X['Time'] = pd.to_datetime(X['Time'], unit='s')
            # Calculate the time difference between each row and the previous one
            X['TimeDifference'] = X['Time'].diff()
            # Find the rows where 'TimeDifference' is greater than 600 seconds (which is 10 minutes)
            gap_indices = X[X['TimeDifference'] > pd.Timedelta(minutes=10)].index
            # Initialize a variable to keep track of the total shift
            total_shift = pd.Timedelta(minutes=0)

            # Loop through all the gap indices
            for ax in gap_indices:
                # Calculate the gap
                gap = X.loc[ax, 'Time'] - X.loc[ax - 1, 'Time']
                # Subtract the total shift from the current gap to get the actual shift for this gap
                actual_shift = gap #- total_shift
                # Add the actual shift to the total shift
                #total_shift += actual_shift
                # Shift the subsequent times
                X.loc[ax:, 'Time'] -= actual_shift
            # Drop the 'TimeDifference' column as it's no longer needed
            X = X.drop(columns=['TimeDifference'])
            X = self.MT_data.convert_time_to_seconds(X)

            gap_timestamps = []
            for ui in gap_indices:
                # Calculate the gap
                gap_timestamps.append(X.loc[ui, 'Time'])
            #print(gap_timestamps)
            #######################################################################################
            last_row_index = train_data.index[-1]
            training_end = X['Time'].iloc[last_row_index]

            cols_to_keep_Power = [col for col in temp_data.columns if 'Power' in col or col == 'Time']
            Features_power = temp_data[cols_to_keep_Power]
            if 'Time' in cols_to_keep_Power:
                cols_to_keep_Power.remove('Time')
            temp_data = temp_data.drop(columns=cols_to_keep_Power)
            box4 = False
            if not cols_to_keep_Power:
                box4 = False
            else:
                box4 = True

            # Plotting
            if box4:
                fig, axs = plt.subplots(4, 1, figsize=(19, 10), sharex=True)
            else:
                fig, axs = plt.subplots(3, 1, figsize=(19, 10), sharex=True)

            colors = color_dict[key] if multicolor_allowed else 'red'

            # Plot 1: Displacement and Predicted Displacement
            axs[0].plot(X['Time'] / 3600, X.iloc[:, 2:], label=f'Measured $E_{{{key}}}$', color=colors,
                        linewidth=1.5)
            axs[0].plot(X['Time'] / 3600, predictions.iloc[:, 2:], label=f'Predicted $E_{{{key}}}$',
                        linestyle='--', color=colors, linewidth=1.5)
            axs[0].axvline(training_end / 3600, color='black', label='Training End', linestyle='-')
            if gap_timestamps:
                for timestamp in gap_timestamps:
                    axs[0].axvline(timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)
            axs[0].set_title(f'{self.ModelType} Compensation Model for $E_{{{key}}}$', fontsize=16, loc='center')
            axs[0].set_title(f'Reduction of RMSE: {round(reduced_thermal_error * 100, 1)}%', fontsize=16, loc='right')  # add in title {reduced_thermal_error}
            # axs[0].set_xlabel('Time [h]', fontsize=16)
            axs[0].set_ylabel('Thermal Error [μm]', fontsize=16)
            axs[0].tick_params(axis='both', labelsize=16)
            axs[0].legend(loc='lower center', ncol=3, fontsize=12)

            residuals = X.iloc[:, 2:] - predictions.iloc[:, 2:]
            # predictions = pd.concat([predictions], axis=0)
            residuals = pd.concat([residuals], axis=0)

            # Plot 2: Residuals
            axs[1].plot(X['Time'] / 3600, residuals, color=colors, linewidth=1.5)
            axs[1].legend(['Residual'], loc='upper right', fontsize=12)
            # axs[1].set_xlabel('Time [h]', fontsize=16)
            axs[1].set_ylabel('Thermal Error [μm]', fontsize=16)
            axs[1].set_title(r'Residual Error Compensation Model $E_{' + f'{key}' + '}$', fontsize=16)
            axs[1].tick_params(axis='both', labelsize=16)
            axs[1].axvline(training_end / 3600, color='black', linestyle='-')
            if gap_timestamps:
                for timestamp in gap_timestamps:
                    axs[1].axvline(timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)

            # Plot 3: Temperature
            a = 0
            for column in temp_data.columns[1:]:
                axs[2].plot(X['Time'] / 3600, temp_data[column], label=column, linewidth=1.5,
                            color=colors_list_input[a])
                a = a + 1
            axs[2].set_xlabel('Time [h]', fontsize=16)
            axs[2].set_ylabel('△ Temperature [K]', fontsize=16)
            axs[2].set_title(f'Model Inputs', fontsize=16)
            axs[2].tick_params(axis='both', labelsize=16)
            if len(temp_data.columns[1:]) > 10 and not box4:
                axs[2].legend(loc='lower center', ncol=7, bbox_to_anchor=(0.5, -0.8), fontsize=12)
            else:
                axs[2].legend(loc='lower center', ncol=7, fontsize=12)
            axs[2].axvline(training_end / 3600, color='black', linestyle='-')
            if gap_timestamps:
                for timestamp in gap_timestamps:
                    axs[2].axvline(timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)

            # Plot 4: Power
            if box4:
                a = 0
                for column in Features_power.columns[1:]:
                    axs[3].plot(X['Time'] / 3600, Features_power[column], label=column, linewidth=1.5,
                                color=colors_list_input[a])
                    a = a + 1
                axs[3].set_xlabel('Time [h]', fontsize=16)
                axs[3].set_ylabel('△ Power [W]', fontsize=16)
                axs[3].set_title(f'Model Inputs', fontsize=16)
                axs[3].tick_params(axis='both', labelsize=16)
                if len(Features_power.columns[1:]) > 3:
                    axs[3].legend(loc='lower center', ncol=6, bbox_to_anchor=(0.5, -0.8), fontsize=12)
                else:
                    axs[3].legend(loc='lower center', ncol=7, fontsize=12)
                axs[3].axvline(training_end / 3600, color='black', linestyle='-')

                if gap_timestamps:
                    for timestamp in gap_timestamps:
                        axs[3].axvline(timestamp/3600, color='red', linestyle='-', linewidth=5, alpha=0.55)

            for ax in axs:
                ax.grid(True)

            plt.tight_layout()
            plt.savefig(
                f'C:\\Users\\mzorzini\\OneDrive - ETH Zurich\\Zorzini_Inspire\\Semester_Project\\Weekly\\Weekly 10\\Bilder\\ARX\\{key}_{i}.png',
                dpi=300)
            i += 1
            plt.show()
            # plt.close()

    def plot_comp_results_OnlyPower_OFFLINE(self, MT_data):
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
                       'salmon', 'gold', 'skyblue', 'olive']

        color_dict = {
            'X0B': 'red',
            'Y0B': 'green',
            'Z0B': 'blue',
            'X0C': 'darkred',
            'Y0C': 'darkgreen',
            'A0B': 'red',
            'C0B': 'blue',
            'B0B': 'green',
            'A0C': 'darkred',
            'C0C': 'darkblue',
            'B0C': 'darkgreen',
            'X0X': 'red',
            'Y0Y': 'green',
            'Z0Z': 'blue',
            'Y0X': 'green',
            'Z0X': 'blue',
            'A0X': 'red',
            'C0X': 'blue',
            'B0X': 'green',
            'A0Y': 'red',
            'C0Y': 'blue',
            'B0Y': 'green',
            'A0Z': 'red',
            'C0Z': 'blue',
            'B0Z': 'green',
            'X0Y': 'red',
            'X0Z': 'red',
            'Y0Z': 'green',
            'X0A': 'red',
            'Y0A': 'green',
            'Z0A': 'blue',
            'A0A': 'red',
            'C0A': 'blue',
            'B0A': 'green'
        }

        colors_list_input = ['orange', 'cyan', 'magenta', 'yellow', 'red', 'green', 'blue', 'purple', 'pink', 'brown',
                             'black', 'teal', 'coral', 'lightblue', 'lime', 'lavender', 'turquoise', 'darkgreen', 'tan',
                             'salmon', 'gold', 'skyblue', 'olive', 'indigo', 'maroon', 'navy', 'khaki', 'ivory',
                             'silver', 'plum', 'orchid', 'beige', 'sienna', 'tomato', 'bisque', 'slateblue',
                             'yellowgreen',
                             'seagreen', 'palegreen', 'peachpuff', 'linen']

        # Iterate over the keys in the dictionaries
        i = 0
        for idx, key in enumerate(self.MT_data.Full_Predicted_bucket.keys()):
            predictions = self.MT_data.Full_Predicted_bucket[key]
            temp_data = self.MT_data.Full_Input_bucket[key]
            X = pd.concat([self.MT_data.Train_Output_bucket[key], self.MT_data.Test_Output_bucket[key]])
            X.reset_index(drop=True,
                          inplace=True)  # because self.MT_data.Train_Output_bucket starts at index 0, else wont recognize it
            train_data = self.MT_data.Train_Output_bucket[key]
            direction = self.MT_data.Full_Predicted_bucket[key]['Wert_1'].iloc[-1]
            reduced_thermal_error = self.MT_data.Total_reduced_RMSE[key]
            train_data = self.MT_data.convert_time_to_seconds(train_data)
            temp_data = self.MT_data.convert_time_to_seconds(temp_data)
            X = self.MT_data.convert_time_to_seconds(X)
            #######################################################################################
            # Shift the times to close the gaps
            #######################################################################################
            # Ensure that 'Time' column is in datetime format
            X['Time'] = pd.to_datetime(X['Time'], unit='s')
            # Calculate the time difference between each row and the previous one
            X['TimeDifference'] = X['Time'].diff()
            # Find the rows where 'TimeDifference' is greater than 600 seconds (which is 10 minutes)
            gap_indices = X[X['TimeDifference'] > pd.Timedelta(minutes=10)].index
            # Initialize a variable to keep track of the total shift
            total_shift = pd.Timedelta(minutes=0)

            # Loop through all the gap indices
            for ax in gap_indices:
                # Calculate the gap
                gap = X.loc[ax, 'Time'] - X.loc[ax - 1, 'Time']
                # Subtract the total shift from the current gap to get the actual shift for this gap
                actual_shift = gap #- total_shift
                # Add the actual shift to the total shift
                #total_shift += actual_shift
                # Shift the subsequent times
                X.loc[ax:, 'Time'] -= actual_shift
            # Drop the 'TimeDifference' column as it's no longer needed
            X = X.drop(columns=['TimeDifference'])
            X = self.MT_data.convert_time_to_seconds(X)

            gap_timestamps = []
            for ui in gap_indices:
                # Calculate the gap
                gap_timestamps.append(X.loc[ui, 'Time'])
            #print(gap_timestamps)
            #######################################################################################
            last_row_index = train_data.index[-1]
            training_end = X['Time'].iloc[last_row_index]

            cols_to_keep_Power = [col for col in temp_data.columns if 'Power' in col or col == 'Time']
            Features_power = temp_data[cols_to_keep_Power]
            if 'Time' in cols_to_keep_Power:
                cols_to_keep_Power.remove('Time')
            temp_data = temp_data.drop(columns=cols_to_keep_Power)

            # Plotting

            fig, axs = plt.subplots(3, 1, figsize=(19, 10), sharex=True)

            colors = color_dict[key] if multicolor_allowed else 'red'

            # Plot 1: Displacement and Predicted Displacement
            axs[0].plot(X['Time'] / 3600, X.iloc[:, 2:], label=f'Measured $E_{{{key}}}$', color=colors,
                        linewidth=1.5)
            axs[0].plot(X['Time'] / 3600, predictions.iloc[:, 2:], label=f'Predicted $E_{{{key}}}$',
                        linestyle='--', color=colors, linewidth=1.5)
            axs[0].axvline(training_end / 3600, color='black', label='Training End', linestyle='-')
            if gap_timestamps:
                for timestamp in gap_timestamps:
                    axs[0].axvline(timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)
            axs[0].set_title(f'{self.ModelType} Compensation Model for $E_{{{key}}}$', fontsize=16, loc='center')
            axs[0].set_title(f'Reduction of RMSE: {round(reduced_thermal_error * 100, 1)}%', fontsize=16, loc='right')  # add in title {reduced_thermal_error}
            # axs[0].set_xlabel('Time [h]', fontsize=16)
            axs[0].set_ylabel('Thermal Error [μm]', fontsize=16)
            axs[0].tick_params(axis='both', labelsize=16)
            axs[0].legend(loc='lower center', ncol=3, fontsize=12)

            residuals = X.iloc[:, 2:] - predictions.iloc[:, 2:]
            # predictions = pd.concat([predictions], axis=0)
            residuals = pd.concat([residuals], axis=0)

            # Plot 2: Residuals
            axs[1].plot(X['Time'] / 3600, residuals, color=colors, linewidth=1.5)
            axs[1].legend(['Residual'], loc='upper right', fontsize=12)
            # axs[1].set_xlabel('Time [h]', fontsize=16)
            axs[1].set_ylabel('Thermal Error [μm]', fontsize=16)
            axs[1].set_title(r'Residual Error Compensation Model $E_{' + f'{key}' + '}$', fontsize=16)
            axs[1].tick_params(axis='both', labelsize=16)
            axs[1].axvline(training_end / 3600, color='black', linestyle='-')
            if gap_timestamps:
                for timestamp in gap_timestamps:
                    axs[1].axvline(timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)

            # Plot 3: Power
            a = 0
            for column in Features_power.columns[1:]:
                axs[2].plot(X['Time'] / 3600, Features_power[column], label=column, linewidth=1.5,
                            color=colors_list_input[a])
                a = a + 1
            axs[2].set_xlabel('Time [h]', fontsize=16)
            axs[2].set_ylabel('△ Power [W]', fontsize=16)
            axs[2].set_title(f'Model Inputs', fontsize=16)
            axs[2].tick_params(axis='both', labelsize=16)
            if len(Features_power.columns[1:]) > 3:
                axs[2].legend(loc='lower center', ncol=7, bbox_to_anchor=(0.5, -0.8), fontsize=12)
                """
                # legend = axs[2].legend(loc='lower center', ncol=6, bbox_to_anchor=(0.5, -0.8), fontsize=12)  # Comment out this line
                # Create a new figure
                fig_leg = plt.figure(figsize=(30, 1))
                ax_leg = fig_leg.add_subplot(111)
                # Add the legend from your plot to the new figure
                ax_leg.legend(*axs[2].get_legend_handles_labels(), loc='center', ncol=7)  # Get the legend from axs[2] directly
                # Hide the axes frame and the x and y labels
                ax_leg.axis('off')
                fig_leg.savefig(f'C:\\Users\\mzorzini\\OneDrive - ETH Zurich\\Zorzini_Inspire\\Semester_Project\\Weekly\\Weekly 10\\Bilder\\ARX\\legends\\{key}_legend_{i}.png', dpi=300)
                """
            else:
                axs[2].legend(loc='lower center', ncol=6, fontsize=12)
            axs[2].axvline(training_end / 3600, color='black', linestyle='-')

            if gap_timestamps:
                for timestamp in gap_timestamps:
                    axs[2].axvline(timestamp/3600, color='red', linestyle='-', linewidth=5, alpha=0.55)

            for ax in axs:
                ax.grid(True)

            plt.tight_layout()
            plt.savefig(
                f'C:\\Users\\mzorzini\\OneDrive - ETH Zurich\\Zorzini_Inspire\\Semester_Project\\Weekly\\Weekly 10\\Bilder\\ARX\\{key}_{i}.png',
                dpi=300)
            i += 1
            plt.show()
            # plt.close()

