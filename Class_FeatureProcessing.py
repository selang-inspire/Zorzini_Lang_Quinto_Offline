import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from colorama import Fore, Style
from threading import Thread
from Class_Machine_General_Data import Machine_Data
from Class_DataFromInflux import InfluxDBQuery
import matplotlib.pyplot as plt
from pytz import timezone

class FeatureProcessing:
    def __init__(self, FeatureData, MT_General, TempSensorsNames, mode, EnergySet, PowerSet, IndigTempSet):
        self.mode = mode
        self.MT_general = MT_General
        self.FeatureData = FeatureData.copy()
        self.TempSensorsNames = TempSensorsNames
        self.Non_TemperatureSensorsNames = [x for x in self.FeatureData.columns if x not in self.TempSensorsNames]
        self.TempSensorsNames = ["Time"] + self.TempSensorsNames
        self.EnergyNames = ["Time"] + EnergySet
        self.PowerNames = ["Time"] + PowerSet
        self.IndigenousTempNames = ["Time"] + IndigTempSet
        self.TemperatureSensorsData = self.FeatureData[self.TempSensorsNames].copy()
        self.Non_TempSensorData = self.FeatureData[self.Non_TemperatureSensorsNames]
        self.NonZeroData = self.del_ZeroColumns()
        self.NonZeroData = self.NonZeroData.iloc[0:len(self.MT_general.Global_Meas_Time_Energy)]
        self.calculate_internal_sampling_time()
        #self.NonZeroData.to_csv(r'C:\Users\mzorzini\Documents\Features.csv', index = False)

        #extract Energy, Power, indigenous Temperature & store raw feature data int Datamanager
        self.Features_energy, self.Features_power_meas, self.Features_Temperature = self.ExtractFeatureSources(self.NonZeroData)
        self.store_raw_feature_data(self.Features_energy, self.Features_power_meas, self.Features_Temperature)

        #apply moving average and exponential moving average to indigenous temperature data
        self.smooth_features_Temperature_MA, self.smooth_exp_Temperature = self.TemperatureProcessing(self.Features_Temperature)

        #Feature Creation: Energy to Power
        self.smooth_energy, self.Features_Power_calculated, self.Features_Power_NonSmoothed = self.EnergyToPower(self.Features_energy)

        #Store processed Features
        self.store_processed_features()

    def store_processed_features(self):
        self.MT_general.processed_indigenous_temperature_data = self.smooth_features_Temperature_MA
        self.MT_general.processed_Energy_Data = self.smooth_energy
        self.MT_general.processed_Power_Data = self.Features_Power_calculated
        self.MT_general.processed_Power_withoutSmoothedEnergy = self.Features_Power_NonSmoothed

    def calculate_internal_sampling_time(self):
        datetime_values = [t[1] for t in self.MT_general.Global_Meas_Time_Energy if t[0] == 'temperature']
        swiss_tz = timezone('Europe/Zurich')  # UTC conversion
        timestamps_swiss = [timestamp.astimezone(swiss_tz) for timestamp in datetime_values]  # UTC conversion
        time_column = pd.Series(timestamps_swiss)  # UTC conversion
        # Assign new values to 'Time' column
        self.NonZeroData['Time'] = time_column
        self.NonZeroData['Time'] = pd.to_datetime(self.NonZeroData['Time']).dt.strftime('%Y-%m-%d %H:%M:%S.%f').str[:-3]

    def del_ZeroColumns(self):
        '''
        - This function deletes columns with only zero values
        '''
        NonZeroData = self.Non_TempSensorData.loc[:, (self.Non_TempSensorData != 0).any(axis=0)]
        NonZeroData = NonZeroData.copy()
        NonZeroData.drop(columns=['Spindle back left casting'], inplace=True) #TODO: Remove this line
        return NonZeroData


    def ExtractFeatureSources(self, Data):
        '''
        Extracts the different feature sources from the Data
        - Energy
        - Power
        - Indigenous Temperature
        '''
        FeatureData = Data.copy() #copy of data to not overwrite
        cols_to_keep_Energy = self.EnergyNames #['Time', 'A-drive Energy', 'B-drive Energy', 'C-drive Energy', 'C-drive rot Energy', 'GX_evo Energy', 'S-drive (grinding) Energy', 'S2-drive (dress) Energy', 'U-drive Energy', 'US-drive Energy', 'X-drive Energy', 'Y-drive Energy', 'Z-drive (Pallette) Energy'] #[col for col in FeatureData.columns if 'Energy' in col or col == 'Time'] #keep only columns with 'Energy' in the name
        cols_to_keep_Power = self.PowerNames #['Time', 'A-drive Power', 'C-drive Power', 'C-drive rot Power', 'S-drive (grinding) Power', 'X-drive Power', 'Y-drive Power', 'Z-drive (Pallette) Power'] #[col for col in FeatureData.columns if 'Power' in col or col == 'Time'] #keep only columns with 'Power' in the name
        cols_to_keep_Temp = self.IndigenousTempNames #['Time', 'A-drive Temperature', 'B-drive Temperature', 'C-drive Temperature', 'C-drive rot Temperature', 'GX_evo Temperature', 'S-drive (grinding) Temperature', 'S2-drive (dress) Temperature', 'U-drive Temperature', 'US-drive Temperature', 'X-drive Temperature', 'Y-drive Temperature', 'Z-drive (Pallette) Temperature'] #[col for col in FeatureData.columns if 'Temperature' in col or col == 'Time'] #keep only columns with 'Temperature' in the name
        Features_energy = FeatureData[cols_to_keep_Energy]
        Features_power_meas = FeatureData[cols_to_keep_Power]
        Features_Temperature = FeatureData[cols_to_keep_Temp]
        return Features_energy, Features_power_meas, Features_Temperature

    def store_raw_feature_data(self, Features_energy, Features_power_meas, Features_Temperature):
        '''
        Store the raw feature data in the Machine General Class
        '''
        self.MT_general.Raw_Energy_Data = Features_energy
        self.MT_general.Raw_Power_Data = Features_power_meas
        self.MT_general.Raw_Indigenous_Temperature_Data = Features_Temperature

    """
    def apply_moving_average(self, df, window_size):
        df_smooth = df.copy()
        for column in df.columns:
            if column != 'Time':
                df_smooth[column] = df[column].rolling(window=window_size, min_periods=1).mean()
        return df_smooth

    """

    def apply_moving_average(self, df, window_size):
        time_threshold = 600  # 10 minutes in seconds
        df_smooth = df.copy()
        df_smooth['Time'] = pd.to_datetime(df_smooth['Time'])
        df_smooth['Time_diff'] = df_smooth['Time'].diff().dt.total_seconds()
        split_indices = df_smooth[df_smooth['Time_diff'] > time_threshold].index.tolist()

        dfs = np.split(df_smooth, split_indices)
        for i in range(len(dfs)):
            for column in dfs[i].columns:
                if column != 'Time' and column != 'Time_diff':
                    dfs[i][column] = dfs[i][column].rolling(window=window_size, min_periods=1).mean()
            dfs[i].drop(columns=['Time_diff'], inplace=True)

        df_smooth = pd.concat(dfs)
        return df_smooth

    def apply_exp_moving_average(self, df, alpha):
        df_smooth = df.copy()
        for column in df.columns:
            if column != 'Time':
                # df_smooth[column] = df[column].rolling(window=window_size, min_periods=1).mean()
                df_smooth[column] = df[column].ewm(alpha=alpha).mean()  # exponential moving average
        return df_smooth

    def convert_time_to_seconds(self, df, time_column='Time'):
        df.loc[:, time_column] = pd.to_datetime(df[time_column])
        first_time = df.loc[0, time_column]
        df.loc[:, time_column] = df.loc[:, time_column].apply(lambda x: (x - first_time).total_seconds())
        return df

    def plot_temperature_data(self, df):
        data = df.copy()
        data = self.convert_time_to_seconds(data, 'Time')

        # Assuming df is your DataFrame and 'Column 0' is the column you're interested in
        data['Difference'] = data['Time'].diff()
        # Find the indices where the difference is greater than 10*60
        indices = data[data['Difference'] > 10 * 60].index.tolist()
        data = data.drop(columns = ['Difference'])
        # Loop through all the gap indices
        for ax in indices:
            # Calculate the gap
            gap = data.loc[ax, 'Time'] - data.loc[ax - 1, 'Time']
            # Subtract the total shift from the current gap to get the actual shift for this gap
            actual_shift = gap  # - total_shift
            # Add the actual shift to the total shift
            # total_shift += actual_shift
            # Shift the subsequent times
            data.loc[ax:, 'Time'] -= actual_shift

        gap_time = []
        for ui in indices:
            gap_time.append(data.loc[ui, 'Time'])

        plt.figure(figsize=(15, 10))
        colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c',
                  '#fabebe', '#008080', '#e6beff']
        for i, column in enumerate(data.drop(columns=['Time']).columns):
            color = colors[i % len(colors)]  # Cycle through colors list
            plt.plot(data['Time'] / 3600, data[column], label=column, linewidth=2, color=color)

        if gap_time:
            for timestamp in gap_time:
                plt.axvline(x=timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)
        plt.xlabel('Time [h]', fontsize=18)
        plt.ylabel('Temperature [°C]', fontsize=18)
        plt.title(f'Indigenous Temperature Data', fontsize=18)
        plt.legend(ncols=5, fontsize=11, loc='upper center',bbox_to_anchor=(0.5, -0.07))
        plt.tick_params(axis='both', labelsize=16)
        plt.grid(True)
        plt.savefig(f'C:\\Users\\mzorzini\\OneDrive - ETH Zurich\\Zorzini_Inspire\\Semester_Project\\Weekly\\weekly 9\\Bilder\\Indig_Temp\\All_Temp_Data.png', dpi=300)
        plt.show()
        plt.close()

    def plot_original_and_smoothed(self, df, MA, EXP):
        original_df = df.copy()
        smoothed_df = MA.copy()
        smoothed_exp_df = EXP.copy()
        original_df = self.convert_time_to_seconds(original_df, 'Time')
        smoothed_df = self.convert_time_to_seconds(smoothed_df, 'Time')
        smoothed_exp_df = self.convert_time_to_seconds(smoothed_exp_df, 'Time')
        i = 0

        ###############################Delete Jumps in Time############################################
        # Assuming df is your DataFrame and 'Column 0' is the column you're interested in
        original_df['Difference'] = original_df['Time'].diff()
        # Find the indices where the difference is greater than 10*60
        indices = original_df[original_df['Difference'] > 10 * 60].index.tolist()
        original_df = original_df.drop(columns=['Difference'])
        # Loop through all the gap indices
        for ax in indices:
            # Calculate the gap
            gap = original_df.loc[ax, 'Time'] - original_df.loc[ax - 1, 'Time']
            # Subtract the total shift from the current gap to get the actual shift for this gap
            actual_shift = gap  # - total_shift
            # Add the actual shift to the total shift
            # total_shift += actual_shift
            # Shift the subsequent times
            original_df.loc[ax:, 'Time'] -= actual_shift

        gap_time = []
        for ui in indices:
            gap_time.append(original_df.loc[ui, 'Time'])

        for column in original_df.drop(columns=['Time']).columns:
            fig, axs = plt.subplots(1, 1, figsize=(10, 5))  # Create a figure with 2 subplots arranged in a 1x2 grid

            # Plot original data
            axs.plot(original_df['Time'] / 3600, original_df[column], color='blue', linewidth=2, label='Original')
            axs.plot(original_df['Time'] / 3600, smoothed_exp_df[column], color='red', linewidth=2, linestyle='dashed', label='EWMA')
            axs.plot(original_df['Time'] / 3600, smoothed_df[column], color='orange', linewidth=2, linestyle='dashed', label='MA')
            for timestamp in gap_time:
                axs.axvline(x=timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)
            axs.set_xlabel('Time [h]', fontsize=16)
            axs.set_ylabel('Temperature [°C]', fontsize=16)
            axs.set_title(f'{column}', fontsize=16)
            axs.grid(True)
            axs.legend(fontsize=14)
            axs.tick_params(axis='both', labelsize=16)

            plt.tight_layout()
            # plt.show()
            plt.savefig(f'C:\\Users\\mzorzini\\OneDrive - ETH Zurich\\Zorzini_Inspire\\Semester_Project\\Weekly\\weekly 9\\Bilder\\Indig_Temp\\{column}.png', dpi=300)
            i += 1
            plt.show()
            plt.close()

    def plot_power_and_original_and_energy_w_wo_smoothed_separated_exp(self, original_energy, Features_Power, Features_power_meas, Features_Energy_smoothed, Features_Power_NonSmoothed):
        # convert to seconds
        original_energy = self.convert_time_to_seconds(original_energy, 'Time')
        Features_Power = self.convert_time_to_seconds(Features_Power, 'Time')
        Features_power_meas = self.convert_time_to_seconds(Features_power_meas, 'Time')
        Features_Energy_smoothed = self.convert_time_to_seconds(Features_Energy_smoothed, 'Time')
        Features_Power_NonSmoothed = self.convert_time_to_seconds(Features_Power_NonSmoothed, 'Time')
        # Plot Energy
        i = 0
        ###############################Delete Jumps in Time############################################
        # Assuming df is your DataFrame and 'Column 0' is the column you're interested in
        original_energy['Difference'] = original_energy['Time'].diff()
        # Find the indices where the difference is greater than 10*60
        indices = original_energy[original_energy['Difference'] > 10 * 60].index.tolist()
        original_energy = original_energy.drop(columns=['Difference'])
        # Loop through all the gap indices
        for ax in indices:
            # Calculate the gap
            gap = original_energy.loc[ax, 'Time'] - original_energy.loc[ax - 1, 'Time']
            # Subtract the total shift from the current gap to get the actual shift for this gap
            actual_shift = gap  # - total_shift
            # Add the actual shift to the total shift
            # total_shift += actual_shift
            # Shift the subsequent times
            original_energy.loc[ax:, 'Time'] -= actual_shift

        gap_time = []
        for ui in indices:
            gap_time.append(original_energy.loc[ui, 'Time'])

        for column in Features_Energy_smoothed.drop(columns=['Time']).columns:
            power_column = column.replace('Energy', 'Power')
            if power_column in Features_power_meas.columns:
                fig, axs = plt.subplots(4, 1, figsize=(20, 10), sharex=True)
            else:
                fig, axs = plt.subplots(3, 1, figsize=(20, 10), sharex=True)  # Create a figure with 2 subplots arranged in a 1x2 grid

            axs[0].plot(original_energy['Time'] / 3600, original_energy[column] / 3600, label='Raw', linewidth=2, color='blue')
            axs[0].plot(Features_Energy_smoothed['Time'] / 3600, Features_Energy_smoothed[column] / 3600, label='Smoothed (MA)', linewidth=2, color='orange', linestyle='dashed')
            # axs[0].set_xlabel('Time [h]', fontsize=16)
            if gap_time:
                for timestamp in gap_time:
                    axs[0].axvline(timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)
            axs[0].set_ylabel('Energy [Wh]', fontsize=20)
            axs[0].legend(loc='best', ncol=3, fontsize=18)
            axs[0].set_title(f'{column}', fontsize=20)
            axs[0].grid(True)
            axs[0].tick_params(axis='both', labelsize=20)

            axs[1].plot(original_energy['Time'] / 3600, Features_Power_NonSmoothed[power_column], label='Power w/ Raw Energy', linewidth=2, color='green')
            # axs[1].set_xlabel('Time [h]', fontsize=16)
            if gap_time:
                for timestamp in gap_time:
                    axs[1].axvline(timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)
            axs[1].set_ylabel('Power [W]', fontsize=20)
            axs[1].grid(True)
            # axs[1].legend(loc='upper center', ncol=2, fontsize=14)
            axs[1].set_title(f'{power_column} Calculated with Raw Data', fontsize=20)
            axs[1].tick_params(axis='both', labelsize=20)

            axs[2].plot(original_energy['Time'] / 3600, Features_Power[power_column], label='Power w/ Smoothed MA', linewidth=2, color='green')
            if power_column not in Features_power_meas.columns:
                axs[2].set_xlabel('Time [h]', fontsize=20)
            if gap_time:
                for timestamp in gap_time:
                    axs[2].axvline(timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)
            axs[2].set_ylabel('Power [W]', fontsize=20)
            axs[2].grid(True)
            #axs[2].legend(loc='best', ncol=2, fontsize=18)
            axs[2].set_title(f'{power_column} Calculated with Smoothed Data', fontsize=20)
            axs[2].tick_params(axis='both', labelsize=20)

            if power_column in Features_power_meas.columns:
                axs[3].plot(original_energy['Time'] / 3600, Features_power_meas[power_column], label='Raw Power Data',
                            linewidth=2, color='green')
                if gap_time:
                    for timestamp in gap_time:
                        axs[3].axvline(timestamp / 3600, color='red', linestyle='-', linewidth=5, alpha=0.55)
                axs[3].set_xlabel('Time [h]', fontsize=20)
                axs[3].set_ylabel('Power [W]', fontsize=20)
                axs[3].grid(True)
                # axs[3].legend(loc='upper center', ncol=2, fontsize=14)
                axs[3].set_title(f'Measured {power_column}', fontsize=20)
                axs[3].tick_params(axis='both', labelsize=20)

            plt.tight_layout()
            plt.savefig(f'C:\\Users\\mzorzini\\OneDrive - ETH Zurich\\Zorzini_Inspire\\Semester_Project\\Weekly\\weekly 9\\Bilder\\EnergyToPower\\{column}.png', dpi=300)
            i += 1
            plt.show()
            plt.close()

    def calculate_power(self, df):
        # Create a new DataFrame for power and time columns
        df['Time'] = pd.to_datetime(df['Time'])
        power_df = pd.DataFrame()
        power_df['Time'] = df['Time']
        # Calculate time differences
        df['Time_diff'] = df['Time'].diff().dt.total_seconds()
        # Iterate over each column (excluding 'Time')
        for col in df.columns:
            if col != 'Time':
                # Calculate power for the current column
                power_df[col.replace('Energy', 'Power')] = df[col].diff() / df['Time_diff']
        # Remove the 'Time_diff' column from the original DataFrame
        # Fill NaN values with the next valid value
        power_df = power_df.bfill()
        df.drop('Time_diff', axis=1, inplace=True)
        power_df.drop('Time_diff', axis=1, inplace=True)
        return power_df

    def TemperatureProcessing(self, Data):
        '''
        - Smooth the Indigenous Temperature Data
        '''
        IndigTempData = Data.copy()
        smooth_features_Temperature_MA = self.apply_moving_average(IndigTempData, window_size=30) #60 equals 5min
        smooth_exp_Temperature = self.apply_exp_moving_average(IndigTempData, alpha=0.05)
        """
        if self.mode == 'Sim':
            self.plot_temperature_data(IndigTempData)
            self.plot_original_and_smoothed(IndigTempData, smooth_features_Temperature_MA, smooth_exp_Temperature)
        """
        return smooth_features_Temperature_MA, smooth_exp_Temperature

    def EnergyToPower(self, Data):
        '''
        - Convert Energy Data to Power Data
        - First smoothing the Energy Data
        - Then calculate the Power Data by differentiating the Energy Data with respect to time
        '''
        EnergyData = Data.copy()
        smooth_energy = self.apply_moving_average(EnergyData, window_size=30)
        Features_Power = self.calculate_power(smooth_energy.copy())
        Features_Power_NonSmoothed = self.calculate_power(EnergyData.copy())
        """
        if self.mode == 'Sim':
            self.plot_power_and_original_and_energy_w_wo_smoothed_separated_exp(EnergyData.copy(), Features_Power.copy(), self.Features_power_meas.copy(), smooth_energy.copy(), Features_Power_NonSmoothed.copy())
        """
        return smooth_energy, Features_Power, Features_Power_NonSmoothed






