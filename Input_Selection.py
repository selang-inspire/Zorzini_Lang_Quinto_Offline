import pandas as pd
from threading import Thread, Event
import csv
import numpy as np
from datetime import datetime
from sklearn.linear_model import LassoCV
from group_lasso import GroupLasso
from sklearn.model_selection import cross_val_score



#Model definition and use
class Input_selection:
    '''
    This class is used to select the inputs for the compensation model
    - The inputs are selected according to the models implemented here
    - LASSO works now, other models can be added #TODO Add other models
    '''
    def __init__(self, MT_General_Data, Input_Selection_Model):
        self.MT_data = MT_General_Data #Access to the global MT_data
        self.InputSelectionType = Input_Selection_Model #Different Model architectures
        self.Input_Model = None #Initializes the Model
        self.InitialData = None #PandaDF which contains the Initial Inputs
        self.Target_Data = None #PandaDF which contains the Target Data / Thermal Error
        self.Input_Normalized_Data = None #PandaDF which contains the Normalized Inputs
        self.Target_Normalized_Data = None #PandaDF which contains the Normalized Target Data
        self.SelectedData = None #PandaDF which contains the Selected Inputs
        self.Selected_Input_Names = None #List of the selected Inputs


    def InputSelectionModel(self, Train_Input_bucket, Train_Output_bucket):
        '''
        - The Input Selection Model is called here
        - The Input Selection Model is used to select the inputs for the compensation model
        - The inputs are selected according to the models called from here
        - If no model available, the initial data is used
        '''
        #Initialize the Data
        self.InitialData = Train_Input_bucket
        self.Target_Data = Train_Output_bucket
        #Normalize the Data
        self.Input_Normalized_Data = self.MT_data.z_score_normalization(self.InitialData, True)
        self.Target_Normalized_Data = self.MT_data.z_score_normalization(self.Target_Data, True)
        #Drop unnecessary columns
        if 'Time' in self.Input_Normalized_Data.columns and 'Time' in self.Target_Normalized_Data.columns:
            self.Input_Normalized_Data = self.Input_Normalized_Data.drop(columns=['Time'])
            self.Target_Normalized_Data = self.Target_Normalized_Data.drop(columns=['Time'])
        if 'Wert_1' in self.Target_Normalized_Data.columns:
            self.Target_Normalized_Data = self.Target_Normalized_Data.drop(columns=['Wert_1'])
        #Select the Inputs
        if self.InputSelectionType == 'LASSO':
            self.Input_LassoCV()
        elif self.InputSelectionType == 'Group LASSO':
            self.Input_GroupLasso()
        else:
            self.No_Input_Selection()

        del self.InitialData, self.Target_Data, self.Input_Normalized_Data, self.Target_Normalized_Data
        return self.SelectedData, self.Selected_Input_Names
        #self.save_in_general_Data()

    def No_Input_Selection(self):
        '''
        - If no model is available, the initial data is used, else it wont work
        '''
        self.SelectedData = self.InitialData
        self.Selected_Input_Names = self.InitialData.columns
        print('Input Selection Model NOT Available')

    def Input_LassoCV(self):
        '''
        - LASSO Model is called here
        - The LASSO Model is used to select the inputs for the compensation model
        - The inputs are selected according to the LASSO Model
        - If no inputs are selected, the model needs to be adjusted
        '''
        self.Input_Model = LassoCV(cv=10, max_iter=10000, tol=0.0001, n_alphas=200, n_jobs=None, random_state=None, selection='cyclic')
        self.Input_Normalized_Data = self.Input_Normalized_Data.dropna(axis=1)
        self.Input_Model.fit(self.Input_Normalized_Data, self.Target_Normalized_Data) #delte NaN columns, else it will not work
        selected_Inputs = self.Input_Normalized_Data.columns[self.Input_Model.coef_ != 0]
        if selected_Inputs.empty:
            self.No_Inputs_Selected()
        else:
            if 'Time' in self.InitialData.columns:
                self.Selected_Input_Names = selected_Inputs.insert(0, 'Time')
            self.SelectedData = self.InitialData[self.Selected_Input_Names]
            print('Selected Inputs are:', selected_Inputs)

    def save_in_general_Data(self): #Not necessary anymore
        '''
        - This def will be used to save the selected inputs in the general data class
        - The output is automatically saved in the general data class
        - Unnecessary data is deleted
        '''
        self.MT_data.SelectedInputs_Train = self.SelectedData
        self.MT_data.Selected_Input_Names = self.Selected_Input_Names
        del self.MT_data, self.InitialData, self.Target_Data, self.Input_Normalized_Data, self.Target_Normalized_Data

    def Input_GroupLasso(self):
        lag_ranges = 3
        lambdas = []
        Neg_RMSE = []
        for iter in range(lag_ranges):
            max_lag = iter
            groups = self.groups_GroupLASSO(max_lag)
            target_scaled, Pre_Selected_Temp_data_combined = self.lagging_GroupLASSO(max_lag)
            # Define a range of group_reg values to explore
            optimal_lambda, best_neg_RMSE = self.find_optimal_lambda_GroupLASSO(groups, target_scaled, Pre_Selected_Temp_data_combined)
            lambdas.append(optimal_lambda)
            Neg_RMSE.append(best_neg_RMSE)
        max_lag = np.argmax(Neg_RMSE)
        optimal_lambda = lambdas[max_lag]
        groups = self.groups_GroupLASSO(max_lag)
        target_scaled, Pre_Selected_Temp_data_combined = self.lagging_GroupLASSO(max_lag)
        self.Input_Model = GroupLasso(groups=groups,group_reg=optimal_lambda,l1_reg=0,supress_warning=True,n_iter=2000)
        self.Input_Model.fit(Pre_Selected_Temp_data_combined, target_scaled)
        selected_feature_indices = [i for i, coef in enumerate(self.Input_Model.coef_) if coef != 0]
        selected_sensors = Pre_Selected_Temp_data_combined.columns[selected_feature_indices]
        selected_sensors = selected_sensors.drop_duplicates()
        if selected_sensors.empty:
            self.No_Inputs_Selected()
        else:
            if 'Time' in self.InitialData.columns:
                self.Selected_Input_Names = selected_sensors.insert(0, 'Time')
            self.SelectedData = self.InitialData[self.Selected_Input_Names]
            print('Selected Inputs are:', selected_sensors)

    def find_optimal_lambda_GroupLASSO(self, groups_1, target_scaled_1, Pre_Selected_Temp_data_combined_1):
        # Define a range of group_reg values to explore
        groups = groups_1
        Pre_Selected_Temp_data_combined = Pre_Selected_Temp_data_combined_1.copy()
        target_scaled = target_scaled_1.copy()
        group_reg_values = np.arange(0.001, 0.02, 0.001) #np.logspace(-2, 1)#np.arange(0.001, 0.02, 0.001)  # adjust this range

        # Initialize variables to store the mean Negative RMSE scores and their corresponding group_reg values
        mean_neg_rmse_scores = []
        # Loop through the group_reg values
        for group_reg_value in group_reg_values:
            # Create a model with the current group_reg value and set l1_reg to 0
            model_group_reg = GroupLasso(groups=groups, group_reg=group_reg_value, l1_reg=0, n_iter=2500, supress_warning=True)
            # Perform cross-validation
            # You can choose the number of folds (e.g., cv=5 for 5-fold cross-validation)
            group_reg_scores = cross_val_score(model_group_reg, Pre_Selected_Temp_data_combined, target_scaled, cv=5, scoring='neg_root_mean_squared_error')
            # Calculate the mean Negative RMSE score for the current group_reg value
            mean_neg_rmse = group_reg_scores.mean()
            # Store the mean Negative RMSE score
            mean_neg_rmse_scores.append(mean_neg_rmse)
        # Find the group_reg value that resulted in the highest mean Negative RMSE score
        best_group_reg = group_reg_values[np.argmax(mean_neg_rmse_scores)]
        # Print the results
        print("Group_reg values:", group_reg_values)
        print("Mean Negative RMSE scores:", mean_neg_rmse_scores)
        print("Best group_reg value:", best_group_reg)
        optimal_lambda = best_group_reg
        return optimal_lambda, max(mean_neg_rmse_scores)

    def lagging_GroupLASSO(self, max_lag):
        '''
        - This def will be used to create the lagged features for the Group LASSO model
        - The lagged features are created according to the number of shifts of rows
        - The lag define how many rows are shifted
        - This function will return the lagged Input data & Target data
        '''
        # Define the number of time steps for the lagged features (look behind values)
        lag_list = np.arange(1, max_lag+1)

        # Initialize the combined dataframes
        Pre_Selected_Temp_data_combined = self.Input_Normalized_Data.copy()
        target_scaled = self.Target_Normalized_Data.copy()

        Orig_Pre_Selected_Temp_data_combined = self.Input_Normalized_Data.copy()
        Orig_target_scaled = self.Target_Normalized_Data.copy()

        # Drop NaN values, else it won't work
        Pre_Selected_Temp_data_combined = Pre_Selected_Temp_data_combined.dropna(axis=1)
        Orig_Pre_Selected_Temp_data_combined = Orig_Pre_Selected_Temp_data_combined.dropna(axis=1)

        # Iterate over the lag_list and create lagged features for each lag
        for lag in lag_list:
            # Create a DataFrame with NaN values
            new_rows = pd.DataFrame(np.nan, index=range(lag), columns=Orig_Pre_Selected_Temp_data_combined.columns)
            new_rows1 = pd.DataFrame(np.nan, index=range(lag), columns=Orig_target_scaled.columns)

            # Append the new rows at the beginning of the existing DataFrame
            Pre_Selected_Temp_data_lagged = pd.concat([new_rows, Orig_Pre_Selected_Temp_data_combined], ignore_index=True)
            target_scaled_lagged = pd.concat([new_rows1, Orig_target_scaled], ignore_index=True)

            # Intersect the indices with the original data
            Pre_Selected_Temp_data_indices = Pre_Selected_Temp_data_lagged.index.intersection(Pre_Selected_Temp_data_combined.index)
            target_scaled_indices = target_scaled_lagged.index.intersection(target_scaled.index)

            # Select the intersected indices
            Pre_Selected_Temp_data_lagged = Pre_Selected_Temp_data_lagged.loc[Pre_Selected_Temp_data_indices]
            target_scaled_lagged = target_scaled_lagged.loc[target_scaled_indices]

            # Concatenate the lagged data with the combined data
            Pre_Selected_Temp_data_combined = pd.concat([Pre_Selected_Temp_data_combined, Pre_Selected_Temp_data_lagged], axis=1)
            target_scaled = pd.concat([target_scaled, target_scaled_lagged], axis=1)

        # Drop NaN values and reset index
        Pre_Selected_Temp_data_combined.dropna(inplace=True)
        target_scaled.dropna(inplace=True)
        Pre_Selected_Temp_data_combined.reset_index(drop=True, inplace=True)
        target_scaled.reset_index(drop=True, inplace=True)

        # Extract only first column of target_scaled
        target_scaled = pd.DataFrame(target_scaled.iloc[:, 0])
        return target_scaled, Pre_Selected_Temp_data_combined

    def groups_GroupLASSO(self, max_lag):
        '''
        - This def will be used to create the groups for the Group LASSO model
        - The groups are created according to the number of Inputs
        - Example for 3 Inputs with 3 Lags:
            [0, 1, 2, 0, 1, 2, 0, 1, 2]
        - Returns an array
        '''
        # Initialize an empty NumPy array
        begin_array = np.array([])
        # Define the range of numbers
        start_num = 0
        df = self.Input_Normalized_Data.dropna(axis=1) #else it won't match with the inputs
        end_num = len(df.T)  # The range is from 0 to 2 (inclusiv-e)
        # Loop through the range and repeat each number three times
        for num in range(start_num, end_num):
            repeated_nums = np.repeat(num, 1)
            begin_array = np.concatenate((begin_array, repeated_nums))
        # Convert the result to a NumPy array
        begin_array = np.array(begin_array)
        # Print the result
        groups = begin_array.copy()
        for _ in range(max_lag):  # subtract 1 because we already have one copy
            groups = np.concatenate((groups, begin_array))
        #groups = np.concatenate((begin_array, begin_array, begin_array, begin_array))
        return groups

    def No_Inputs_Selected(self):
        '''
        - If no inputs are selected, this def will be used
        - The Initial Data is used in this case
        - The user has to adjust the model to get selected inputs
        '''
        print('No Inputs selected, please adjust the Input Selection Model')
        self.SelectedData = self.InitialData
        self.Selected_Input_Names = self.InitialData.columns
        print('Initial Dataframe is used')