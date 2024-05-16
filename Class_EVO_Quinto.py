import pandas as pd
from threading import Thread, Event
import csv
import numpy as np
from datetime import datetime
from OPC_UA_conn import OPCUAcon
from pytz import timezone
import matplotlib.pyplot as plt

#machine specific parameters
class EVO_Quinto:

    def __init__(self,log_file_name):
        #Temperature Sensors installed on MT (you can add or remove sensors from list)
        self.SensorList = ['A axis Drive Structure', 'Air Workingspace', 'Drive grinding spindle', 'Air back', 'B Drive gearbox', 'B WerkstückSpanner links', 'B WerkstückSpanner rechts', 'B drive gap between gear', 'Bed behind machine left, axis enclosure', 'C Axis Cover', 'C axis Top Auf Spindelstock Mitte', 'C axis side down', 'C axis top prisma', 'Coolant Backflow', 'Env Machine Front', 'Env Machine back middle', 'Oil Backflow', 'Spindle Structure Front', 'Touch Probe Holder Spindle', 'X Drive middle top', 'X drive back down', 'X structure cast right', 'bed below front'] #'Spindle back left casting' auskommentiert da dieser Sensor fehlerhaft ist
        self.EngKnowSensorSet = ['A axis Drive Structure', 'Air Workingspace', 'Drive grinding spindle', 'Air back', 'B Drive gearbox', 'B WerkstückSpanner links', 'B WerkstückSpanner rechts', 'B drive gap between gear', 'Bed behind machine left, axis enclosure', 'C Axis Cover', 'C axis Top Auf Spindelstock Mitte', 'Coolant Backflow', 'Env Machine Front', 'Env Machine back middle', 'Oil Backflow', 'Spindle Structure Front', 'Touch Probe Holder Spindle', 'X Drive middle top', 'X drive back down', 'X structure cast right', 'bed below front']
        self.EvalSensorSet = ['A axis Drive Structure','B Drive gearbox','C axis side down','C axis top prisma','Env Machine Front','X drive back down','bed below front']
        self.EnvTempSensorsSet = ['Air Workingspace','Air back','Env Machine Front','Env Machine back middle']
        self.EnergySet = ['A-drive Energy', 'B-drive Energy', 'C-drive Energy', 'C-drive rot Energy', 'S-drive (grinding) Energy', 'X-drive Energy', 'Y-drive Energy'] #['A-drive Energy', 'B-drive Energy', 'C-drive Energy', 'C-drive rot Energy', 'GX_evo Energy', 'S-drive (grinding) Energy', 'S2-drive (dress) Energy', 'U-drive Energy', 'US-drive Energy', 'X-drive Energy', 'Y-drive Energy', 'Z-drive (Pallette) Energy']
        self.PowerSet = ['A-drive Power', 'C-drive Power', 'C-drive rot Power', 'S-drive (grinding) Power', 'X-drive Power', 'Y-drive Power'] #['A-drive Power', 'C-drive Power', 'C-drive rot Power', 'S-drive (grinding) Power', 'X-drive Power', 'Y-drive Power', 'Z-drive (Pallette) Power']
        self.IndigTempSet = ['A-drive Temperature', 'B-drive Temperature', 'C-drive Temperature', 'C-drive rot Temperature', 'GX_evo Temperature', 'S-drive (grinding) Temperature', 'S2-drive (dress) Temperature', 'U-drive Temperature', 'US-drive Temperature', 'X-drive Temperature', 'Y-drive Temperature', 'Z-drive (Pallette) Temperature']

        self.ErrorList = ['X0B', 'Y0B', 'Z0B', 'A0B', 'C0B', 'X0C', 'Y0C']
        self.log_file_name = log_file_name

        #Influx access to Quinto
        self.token = "4MecLF8nQznwGWhGSPQhi6v_Y3dvyoHVqlUvF7JZqEDIZGWqvwdwQQBvZ-oEObwkpCjj4oHb8_uTFm8VmDSYvQ=="
        self.url = "http://isim-ws016.intern.ethz.ch:8086"
        self.org = 'ThermoComp'
        self.queryName = 'Quinto164'
        #mc.FilePathTemperature = r'C:\Users\' #TODO

        self.Reference=9.5;
    def ConnectMachine(self,measurementFrequency):
        self.OPC = OPCUAcon(measurementFrequency,self.log_file_name)
    def OfflineFileData(self):
        #loading from excel
        Temperature = pd.read_excel (self.FilePathTemperature)
        Dx = pd.read_excel (self.FilePathDx)
        Latch = pd.read_excel(self.FilePathLatch)
        
        ThermalError = ThermalErrorCalculation(Dx,Latch,self.Reference)
        Temperature, ThermalError = TableLayout(Temperature,self.SensorList, ThermalError, self.ErrorList)
        
        return ThermalError, Temperature

    #This def will be used to load the error data from the excel file and store it as pandaDF
    def Load_Excel_Error(self, excel_datei, start_time, end_time):
        excel_datei = excel_datei
        df = pd.read_excel(excel_datei)
        last_row_index = df.last_valid_index()
        extracted_df = df.iloc[3:last_row_index+1]  # extract rows from excel file, adjust this if file is larger

        extracted_df = extracted_df.drop(extracted_df.index[0])
        extracted_df = extracted_df.drop(extracted_df.columns[0], axis=1) #TODO make these lines efficient
        extracted_df = extracted_df.drop(extracted_df.columns[1], axis=1)
        extracted_df = extracted_df.drop(extracted_df.columns[1], axis=1)
        extracted_df = extracted_df.drop(extracted_df.columns[1], axis=1)
        extracted_df = extracted_df.rename(columns={extracted_df.columns[0]: 'Time'})

        columns_to_delete = list(range(1, 7)) + list(range(8, 10)) + list(range(11, 16)) + list(range(17, 19)) + [20]
        extracted_df = extracted_df.drop(extracted_df.columns[columns_to_delete], axis=1)
        extracted_df.rename(columns={'Unnamed: 11': 'Wert_1'}, inplace=True)
        extracted_df.rename(columns={'Unnamed: 14': 'Wert_2'}, inplace=True)
        extracted_df.rename(columns={'Unnamed: 20': 'Wert_4'}, inplace=True)
        extracted_df.rename(columns={'Unnamed: 23': 'Wert_5'}, inplace=True)

        extracted_df.drop(columns=['Wert_2', 'Wert_5'], inplace=True)

        extracted_df['Wert_4'] = extracted_df['Wert_4']*1000 #convert [mm] to [um]

        start = start_time #"03/18/2024 04:10:00.00 PM"#extracted_df.iloc[0, 0]
        end = end_time #"03/19/2024 10:59:59.00 AM"#extracted_df.iloc[-1, 0]

        start_datetime = datetime.strptime(start, "%m/%d/%Y %I:%M:%S.%f %p")
        end_datetime = datetime.strptime(end, "%m/%d/%Y %I:%M:%S.%f %p")

        #############Start UTC conversion
        # Define the Swiss timezone #TODO check if conversion necessary, else set influx server timezone?
        swiss_tz = timezone('Europe/Zurich')
        # Localize the datetime to Swiss time
        start_datetime_1 = swiss_tz.localize(datetime.strptime(start, "%m/%d/%Y %I:%M:%S.%f %p"))
        end_datetime_1 = swiss_tz.localize(datetime.strptime(end, "%m/%d/%Y %I:%M:%S.%f %p"))

        start_datetime_UTC = start_datetime_1.astimezone(timezone('UTC'))
        end_datetime_UTC = end_datetime_1.astimezone(timezone('UTC'))

        start_iso = start_datetime_UTC.strftime("%Y-%m-%dT%H:%M:%S.%fZ")  # for influxdb to extract corresponding temp data
        end_iso = end_datetime_UTC.strftime("%Y-%m-%dT%H:%M:%S.%fZ")  # for influxdb to extract corresponding temp data
        #############end UTC conversion

        extracted_df.reset_index(drop=True, inplace=True)
        extracted_df['Time'] = pd.to_datetime(extracted_df['Time']).dt.strftime('%Y-%m-%d %H:%M:%S.%f').str[:-3]

        start_datetime = start_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')
        end_datetime = end_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')

        #filter the data according to the start and end time
        extracted_df['Time'] = pd.to_datetime(extracted_df['Time'])
        filtered_df = extracted_df[(extracted_df['Time'] >= start_datetime) & (extracted_df['Time'] <= end_datetime)]
        extracted_df = filtered_df
        extracted_df.reset_index(drop=True, inplace=True)

        self.Separated_DF = {}
        #reference_Dataframe = pd.DataFrame({'Time': ['0000-00-00 00:00:00'],'Wert_1': [None], 'Wert_4': [0.0]})
        #reference_Dataframe = pd.concat([reference_Dataframe] * 8, ignore_index=True)
        reference_dict = {}

        for value in extracted_df['Wert_1'].unique():
            filtered_df = extracted_df[extracted_df['Wert_1'] == value].reset_index(drop=True)
            first_value = filtered_df['Wert_4'].iloc[0]  # Get the first value of Wert_4 column
            # Subtract the first value from all values in Wert_4 column
            filtered_df['Wert_4'] -= first_value  # mit referenz zu Nullpunkt
            reference_dict[f'Error_{value}'] = pd.DataFrame({'Time': [filtered_df.iloc[0, 0]], 'Wert_1': [filtered_df.iloc[0, 1]], 'Wert_4': [first_value]})
            self.Separated_DF[f'Error_{value}'] = filtered_df

        for key, df in self.Separated_DF.items(): #reset index of all dataframes in the dictionary
            self.Separated_DF[key] = df.reset_index(drop=True)

        #data_error_1 = self.Separated_DF['df_1']
        #data_error_1.reset_index(drop=True, inplace=True)

        #return data_error_1, start_iso, end_iso, reference_Dataframe
        return self.Separated_DF, start_iso, end_iso, reference_dict


    def Calculate_Error(self, DisplData_X, DisplData_Y):
        '''
        This function calculates the thermal error of the machine (specifically the AGATHON Evo Quinto)
        - The thermal error is calculated based on the displacement data of the machine
        - The Error data must eb stored in a dictionary which contains pandas dataframes
            --> The key of the dictionary is the name of the error
            --> The pandas dataframe contains the columns ['Time', 'Wert_1', 'Wert_4']
            --> The 'Wert_1' column contains the name of the error
            --> The 'Wert_4' column contains the calculated error
        '''
        print("Thermal Error Calculation Started")
        #Initialize params and insert new columns
        self.Calc_ThermalError_DF = {}
        reference_dict = {}
        displ_data_X = DisplData_X.copy()
        displ_data_y = DisplData_Y.copy()
        displ_data_X.insert(1, "Antastrichtung", "X")
        displ_data_y.insert(1, "Antastrichtung", "Y")

        # convert mm to um
        displ_data_X['X Axis position'] *= 1000
        displ_data_X['Y Axis position'] *= 1000
        displ_data_y['X Axis position'] *= 1000
        displ_data_y['Y Axis position'] *= 1000

        #create Unified Dataframe (X & Y Antastrichtung together)
        displ_data_X.set_index('Time', inplace=True)
        displ_data_y.set_index('Time', inplace=True)
        Unified_displacement_DF = pd.concat([displ_data_X, displ_data_y])
        Unified_displacement_DF = Unified_displacement_DF.sort_index()
        displ_data_X.reset_index(inplace=True)
        displ_data_y.reset_index(inplace=True)
        Unified_displacement_DF.reset_index(inplace=True)
        del displ_data_X, displ_data_y, DisplData_X, DisplData_Y
        #########################################################################################
        Unified_displacement_DF['C Axis position'] = Unified_displacement_DF['C Axis position'].apply(lambda x: 0 if x < 10 else (90 if 80 < x < 100 else x))
        # Create a helper column that increments each time 'C Axis position' changes from 0 to 90
        Unified_displacement_DF['cycle'] = ((Unified_displacement_DF['C Axis position'] == 0) & (Unified_displacement_DF['C Axis position'].shift() == 90)).cumsum()

        # Group by the 'cycle' column and create a dictionary of dataframes for each measurement cycle
        cycles = {cycle: data.reset_index(drop=True) for cycle, data in Unified_displacement_DF.groupby('cycle')}
        del Unified_displacement_DF
        # ------------------------------------------------------------------------------------------
        """
        # delete manually defined keys
        keys_to_delete = list(range(400, 490))  # Create a list of keys to delete

        for key in keys_to_delete:
            if key in cycles:  # Check if the key exists in the dictionary
                del cycles[key]  # Delete the key-value pair
        # reset keys that it starts from 0 again
        cycles = {i: cycles[key] for i, key in enumerate(cycles.keys())}
        """
        # ------------------------------------------------------------------------------------------
        # identify Time gaps in between cycles and the following cycle, if Timegap of last Time value in previous cycle and first Time value in next cycle is greater than 10 minutes
        # Initialize an empty list to store the keys
        large_gap_cycles = []
        for keys in cycles.keys():
            if keys != 0:
                cycles[keys]['Time'] = pd.to_datetime(cycles[keys]['Time'])
                cycles[keys - 1]['Time'] = pd.to_datetime(cycles[keys - 1]['Time'])
                time_gap = cycles[keys].iloc[0, 0] - cycles[keys - 1].iloc[-1, 0]
                if time_gap > pd.Timedelta(minutes=10):
                    print(f"Time gap between cycle {keys - 1} and {keys} is {time_gap}")
                    # Append the key to the list
                    large_gap_cycles.append(keys)
        # delete keys
        keys_to_delete = []
        for i in range(len(large_gap_cycles) - 1):
            if large_gap_cycles[i + 1] - large_gap_cycles[i] < 12:
                keys_to_delete.extend(range(large_gap_cycles[i], large_gap_cycles[i + 1]))

        for key in keys_to_delete:
            if key in cycles:
                del cycles[key]

        # if first key has dataframe smaller length 25, then delete the first key
        if len(cycles[list(cycles.keys())[0]]) < 25:
            del cycles[list(cycles.keys())[0]]
            print("First cycle deleted")
        #reset keys that it starts from 0 again
        cycles = {i: cycles[key] for i, key in enumerate(cycles.keys())}

        # if in last key in 'C Axis position' is not 90, then delete the last key
        if cycles[list(cycles.keys())[-1]].iloc[-1, 2] != 90:
            del cycles[list(cycles.keys())[-1]]
            print("Last cycle incomplete, deleted")
        # ------------------------------------------------------------------------------------------
        #create dictionary which contain as keys X0B, Y0C
        Error_dict = {
            "X0B": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4']),
            "Y0B": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4']),
            "Z0B": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4']),
            "A0B": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4']),
            "C0B": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4']),
            "Y0C": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4']),
            "A0B_90": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4']),
            "C0B_90": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4']),
            "X0C": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4']),
            "X0B_2": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4']),
            "Y0B_2": pd.DataFrame(columns=['Time', 'Wert_1', 'Wert_4'])
        }
        list_phi = []
        list_phi2 = []
        list_XZ0B1 = []
        list_XZ0B2 = []
        for keys in cycles.keys():
            # Y0B berechnen
            #search indices where 'Antastrichtung' is 4x ina a row 'Y'
            indices_Y0C = cycles[keys].loc[cycles[keys]['Antastrichtung'] == 'Y'].index.tolist()
            if indices_Y0C:
                diff = [j-i for i, j in zip(indices_Y0C[:-1], indices_Y0C[1:])]
                if diff[-1] > 1:
                    indices_Y0C.pop()
                #insert 0°, 90°, 180°, 270° in row ['B Axis position']
                if len(indices_Y0C) == 4:
                    cycles[keys].loc[indices_Y0C, 'B Axis position'] = [0, 90, 180, 270]
                start_index = indices_Y0C[0]
                end_index = indices_Y0C[-1]
                #extract the rows
                selected_rows_Y0C = cycles[keys].loc[start_index:end_index, ['X Axis position', 'Y Axis position']]
                selected_rows_Y0C_time = cycles[keys].loc[start_index:end_index, ['Time']]
                #calculate the mean of the selected rows
                mean_selected_rows_YOC = selected_rows_Y0C.mean()
                selected_rows_Y0C_time['Time'] = pd.to_datetime(selected_rows_Y0C_time['Time'])
                mean_time_y0c = selected_rows_Y0C_time['Time'].min() + (selected_rows_Y0C_time['Time'].max() - selected_rows_Y0C_time['Time'].min()) / 2
                new_row_y0c = pd.DataFrame([[mean_time_y0c, 'Y0B', mean_selected_rows_YOC['Y Axis position']]],columns=['Time', 'Wert_1', 'Wert_4'])
                #insert the value into the dictionary
                new_row_y0c.dropna(inplace=True)
                Error_dict['Y0B'].dropna(inplace=True)
                if not new_row_y0c.empty and not new_row_y0c.isna().all().all():
                    Error_dict['Y0B'] = pd.concat([Error_dict['Y0B'], new_row_y0c], ignore_index=True)
            else:
                print("Missing Y0C at cycle: ", keys)
            # ------------------------------------------------------------------------------------------
            # X0B berechnen
            #search indices where 'Antastrichtung' is 13x ina a row 'X'
            indices_X0B = cycles[keys].loc[cycles[keys]['C Axis position'] == 90].index.tolist()
            start_index_X0B = end_index+1
            end_index_X0B = indices_X0B[0]-1
            if indices_X0B:
                #extract rows
                selected_rows_X0B = cycles[keys].loc[start_index_X0B:end_index_X0B, ['X Axis position', 'Y Axis position']]
                selected_rows_X0B_Time = cycles[keys].loc[start_index_X0B:end_index_X0B, ['Time']]
                #calculate the mean of the selected rows
                mean_selected_rows_X0B = selected_rows_X0B.mean()
                selected_rows_X0B_Time['Time'] = pd.to_datetime(selected_rows_X0B_Time['Time'])
                mean_time_x0b = selected_rows_X0B_Time['Time'].min() + (selected_rows_X0B_Time['Time'].max() - selected_rows_X0B_Time['Time'].min()) / 2
                #insert the value into the dictionary
                new_row_X0c = pd.DataFrame([[mean_time_x0b, 'X0B', mean_selected_rows_X0B['X Axis position']]],columns=['Time', 'Wert_1', 'Wert_4'])
                new_row_X0c.dropna(inplace=True)
                Error_dict['X0B'].dropna(inplace=True)
                if not new_row_X0c.empty and not new_row_X0c.isna().all().all():
                    Error_dict['X0B'] = pd.concat([Error_dict['X0B'], new_row_X0c], ignore_index=True)
            else:
                print("Missing X0B at cycle: ", keys)

            # ------------------------------------------------------------------------------------------
            # Z0B calculation
            # check if the first index form 0 to 5 in column 'Antastrichtung' is X
            list_Z0B = cycles[keys].loc[cycles[keys]['Antastrichtung'] == 'X'].index.tolist()
            # check if 0, 1, 2, 3, 4, 5 are in the list
            list_Z0B = [i for i in list_Z0B if i <= 5]
            #take indices from list_Z0B at which 'MB Axis positon' the value is negative
            list_Z0B_2 = [i for i in list_Z0B if cycles[keys].loc[i, 'MB Axis position'] < 0]
            list_Z0B_3 = [i for i in list_Z0B if cycles[keys].loc[i, 'MB Axis position'] > 0]
            if len(list_Z0B_2) >= 2 and len(list_Z0B_3) >= 2:
                Z0B_variant1 = False
                Z0B_variant2 = False
                Z0B_variant3 = False
                Z0B_variant4 = True #True
                Z0B_variant5 = False
                Z0B_variant6 = False
                if Z0B_variant1:
                    WMESArmRadMB = 314.5*1000
                    indices_first_Z0B = list_Z0B_2
                    indices_second_Z0B = list_Z0B_3
                    #selected rows
                    selected_rows_first_Z0B = cycles[keys].loc[indices_first_Z0B, ['X Axis position', 'MB Axis position']]
                    selected_rows_second_Z0B = cycles[keys].loc[indices_second_Z0B, ['X Axis position', 'MB Axis position']]
                    Time_values_Z0B = cycles[keys].loc[list_Z0B, ['Time']]
                    #calculate mean
                    mean_selected_rows_first_Z0B = selected_rows_first_Z0B.mean()
                    mean_selected_rows_second_Z0B = selected_rows_second_Z0B.mean()
                    Time_values_Z0B['Time'] = pd.to_datetime(Time_values_Z0B['Time'])
                    mean_time__z0b = Time_values_Z0B['Time'].min() + (Time_values_Z0B['Time'].max() - Time_values_Z0B['Time'].min()) / 2
                    # delta phi
                    delta_phi = -mean_selected_rows_first_Z0B['MB Axis position'] + mean_selected_rows_second_Z0B['MB Axis position']
                    delta_x_Z0B = -mean_selected_rows_first_Z0B['X Axis position'] + mean_selected_rows_second_Z0B['X Axis position']
                    Z0B = np.sqrt((np.radians(delta_phi)*WMESArmRadMB)**2 - delta_x_Z0B**2)
                    #insert the value into the dictionary
                    new_row_z0b = pd.DataFrame([[mean_time__z0b, 'Z0B', Z0B]], columns=['Time', 'Wert_1', 'Wert_4'])
                    new_row_z0b.dropna(inplace=True)
                    Error_dict['Z0B'].dropna(inplace=True)
                    if not new_row_z0b.empty and not new_row_z0b.isna().all().all():
                        Error_dict['Z0B'] = pd.concat([Error_dict['Z0B'], new_row_z0b], ignore_index=True)

                if Z0B_variant2:
                    WMESArmRadMB = 314.5*1000
                    indices_first_Z0B = list_Z0B_2
                    indices_second_Z0B = list_Z0B_3
                    #selected rows
                    selected_rows_first_Z0B = cycles[keys].loc[indices_first_Z0B, ['X Axis position', 'MB Axis position']]
                    selected_rows_second_Z0B = cycles[keys].loc[indices_second_Z0B, ['X Axis position', 'MB Axis position']]
                    Time_values_Z0B = cycles[keys].loc[list_Z0B, ['Time']]
                    #calculate mean
                    mean_selected_rows_first_Z0B = selected_rows_first_Z0B.mean()
                    mean_selected_rows_second_Z0B = selected_rows_second_Z0B.mean()
                    Time_values_Z0B['Time'] = pd.to_datetime(Time_values_Z0B['Time'])
                    mean_time__z0b = Time_values_Z0B['Time'].min() + (Time_values_Z0B['Time'].max() - Time_values_Z0B['Time'].min()) / 2
                    # calculate steepnes of curve
                    phi = mean_selected_rows_first_Z0B['MB Axis position']
                    x1 = np.cos(np.radians(phi)) * WMESArmRadMB
                    z1 = np.sin(np.radians(phi)) * WMESArmRadMB
                    # steepnes of tangent
                    m = x1/z1
                    delta_x_Z0B = mean_selected_rows_first_Z0B['X Axis position'] - mean_selected_rows_second_Z0B['X Axis position']
                    Z0B = delta_x_Z0B * m * (-1)
                    #insert the value into the dictionary
                    new_row_z0b = pd.DataFrame([[mean_time__z0b, 'Z0B', Z0B]], columns=['Time', 'Wert_1', 'Wert_4'])
                    new_row_z0b.dropna(inplace=True)
                    Error_dict['Z0B'].dropna(inplace=True)
                    if not new_row_z0b.empty and not new_row_z0b.isna().all().all():
                        Error_dict['Z0B'] = pd.concat([Error_dict['Z0B'], new_row_z0b], ignore_index=True)

                if Z0B_variant3:
                    WMESArmRadMB = 314.5*1000 #in um
                    indices_first_Z0B = list_Z0B_2
                    indices_second_Z0B = list_Z0B_3
                    # extract rows
                    selected_rows_first_Z0B = cycles[keys].loc[indices_first_Z0B, ['X Axis position', 'MB Axis position']]
                    selected_rows_second_Z0B = cycles[keys].loc[indices_second_Z0B, ['X Axis position', 'MB Axis position']]
                    Time_values_Z0B = cycles[keys].loc[list_Z0B, ['Time']]
                    # calculate mean
                    mean_selected_rows_first_Z0B = selected_rows_first_Z0B.mean()
                    mean_selected_rows_second_Z0B = selected_rows_second_Z0B.mean()
                    Time_values_Z0B['Time'] = pd.to_datetime(Time_values_Z0B['Time'])
                    mean_time__z0b = Time_values_Z0B['Time'].min() + (Time_values_Z0B['Time'].max() - Time_values_Z0B['Time'].min()) / 2
                    # calculate the difference in Z
                    delta_x_Z0B = mean_selected_rows_first_Z0B['X Axis position'] - mean_selected_rows_second_Z0B['X Axis position']
                    phi_first_Z0B = mean_selected_rows_first_Z0B['MB Axis position']
                    x1_z0b = np.cos(np.radians(phi_first_Z0B)) * WMESArmRadMB
                    z1_z0b = np.sin(np.radians(phi_first_Z0B)) * WMESArmRadMB
                    z2_z0b = (WMESArmRadMB**2 - (x1_z0b - delta_x_Z0B)**2)**0.5
                    Z0B = z2_z0b
                    # insert the value into the dictionary
                    new_row_z0b = pd.DataFrame([[mean_time__z0b, 'Z0B', Z0B]], columns=['Time', 'Wert_1', 'Wert_4'])
                    new_row_z0b.dropna(inplace=True)
                    Error_dict['Z0B'].dropna(inplace=True)
                    if not new_row_z0b.empty and not new_row_z0b.isna().all().all():
                        Error_dict['Z0B'] = pd.concat([Error_dict['Z0B'], new_row_z0b], ignore_index=True)

                if Z0B_variant4:
                    WMESArmRadMB = 314.5/1000 #in m
                    curvature = 1 / WMESArmRadMB
                    indices_first_Z0B = list_Z0B_2
                    indices_second_Z0B = list_Z0B_3
                    # extract rows
                    selected_rows_first_Z0B = cycles[keys].loc[indices_first_Z0B, ['X Axis position', 'MB Axis position']]
                    selected_rows_second_Z0B = cycles[keys].loc[indices_second_Z0B, ['X Axis position', 'MB Axis position']]
                    Time_values_Z0B = cycles[keys].loc[list_Z0B, ['Time']]
                    # calculate mean
                    mean_selected_rows_first_Z0B = selected_rows_first_Z0B.mean()
                    mean_selected_rows_second_Z0B = selected_rows_second_Z0B.mean()
                    Time_values_Z0B['Time'] = pd.to_datetime(Time_values_Z0B['Time'])
                    mean_time__z0b = Time_values_Z0B['Time'].min() + (Time_values_Z0B['Time'].max() - Time_values_Z0B['Time'].min()) / 2
                    # calculate the difference in X
                    delta_x_Z0B = mean_selected_rows_first_Z0B['X Axis position'] - mean_selected_rows_second_Z0B['X Axis position']
                    Z0B = delta_x_Z0B*curvature
                    # insert the value into the dictionary
                    new_row_z0b = pd.DataFrame([[mean_time__z0b, 'Z0B', Z0B]], columns=['Time', 'Wert_1', 'Wert_4'])
                    new_row_z0b.dropna(inplace=True)
                    Error_dict['Z0B'].dropna(inplace=True)
                    if not new_row_z0b.empty and not new_row_z0b.isna().all().all():
                        Error_dict['Z0B'] = pd.concat([Error_dict['Z0B'], new_row_z0b], ignore_index=True)

                if Z0B_variant5:
                    WMESArmRadMB = 314.5 * 1000
                    indices_first_Z0B = list_Z0B_2
                    indices_second_Z0B = list_Z0B_3
                    # selected rows
                    selected_rows_first_Z0B = cycles[keys].loc[indices_first_Z0B, ['X Axis position', 'MB Axis position']]
                    selected_rows_second_Z0B = cycles[keys].loc[indices_second_Z0B, ['X Axis position', 'MB Axis position']]
                    Time_values_Z0B = cycles[keys].loc[list_Z0B, ['Time']]
                    # calculate mean
                    mean_selected_rows_first_Z0B = selected_rows_first_Z0B.mean()
                    mean_selected_rows_second_Z0B = selected_rows_second_Z0B.mean()
                    Time_values_Z0B['Time'] = pd.to_datetime(Time_values_Z0B['Time'])
                    mean_time__z0b = Time_values_Z0B['Time'].min() + (Time_values_Z0B['Time'].max() - Time_values_Z0B['Time'].min()) / 2
                    # calculate steepnes of curve
                    phi = mean_selected_rows_first_Z0B['MB Axis position']
                    phi2 = mean_selected_rows_second_Z0B['MB Axis position']
                    x1 = np.cos(np.radians(phi)) * WMESArmRadMB
                    x2 = np.cos(np.radians(phi2)) * WMESArmRadMB
                    z1 = np.sin(np.radians(phi)) * WMESArmRadMB
                    z2 = np.sin(np.radians(phi2)) * WMESArmRadMB
                    # steepnes of tangente
                    m = x1 / z1
                    m2 = x2 / z2
                    delta_x_Z0B = mean_selected_rows_first_Z0B['X Axis position'] - mean_selected_rows_second_Z0B['X Axis position']
                    Z0B1 = delta_x_Z0B * m * (-1)
                    Z0B2 = delta_x_Z0B * m2
                    Z0B = (Z0B1 + Z0B2) / 2
                    # insert the value into the dictionary
                    new_row_z0b = pd.DataFrame([[mean_time__z0b, 'Z0B', Z0B]], columns=['Time', 'Wert_1', 'Wert_4'])
                    new_row_z0b.dropna(inplace=True)
                    Error_dict['Z0B'].dropna(inplace=True)
                    if not new_row_z0b.empty and not new_row_z0b.isna().all().all():
                        Error_dict['Z0B'] = pd.concat([Error_dict['Z0B'], new_row_z0b], ignore_index=True)

                if Z0B_variant6:
                    WMESArmRadMB = 314.5 * 1000
                    indices_first_Z0B = list_Z0B_2
                    indices_second_Z0B = list_Z0B_3
                    # selected rows
                    selected_rows_first_Z0B = cycles[keys].loc[indices_first_Z0B, ['X Axis position', 'MB Axis position']]
                    selected_rows_second_Z0B = cycles[keys].loc[indices_second_Z0B, ['X Axis position', 'MB Axis position']]
                    Time_values_Z0B = cycles[keys].loc[list_Z0B, ['Time']]
                    # calculate mean
                    mean_selected_rows_first_Z0B = selected_rows_first_Z0B.mean()
                    mean_selected_rows_second_Z0B = selected_rows_second_Z0B.mean()
                    Time_values_Z0B['Time'] = pd.to_datetime(Time_values_Z0B['Time'])
                    mean_time__z0b = Time_values_Z0B['Time'].min() + (Time_values_Z0B['Time'].max() - Time_values_Z0B['Time'].min()) / 2
                    # calculate steepnes of curve
                    phi = mean_selected_rows_first_Z0B['MB Axis position']
                    phi2 = mean_selected_rows_second_Z0B['MB Axis position']
                    list_phi.append(phi)
                    list_phi2.append(phi2)
                    list_XZ0B1.append(mean_selected_rows_first_Z0B['X Axis position'])
                    list_XZ0B2.append(mean_selected_rows_second_Z0B['X Axis position'])
                    z1 = np.sin(np.radians(phi)) * WMESArmRadMB * (-1)
                    z2 = np.sin(np.radians(phi2)) * WMESArmRadMB
                    # steepnes of tangente
                    Z0B = (z1 + z2)
                    # insert the value into the dictionary
                    new_row_z0b = pd.DataFrame([[mean_time__z0b, 'Z0B', Z0B]], columns=['Time', 'Wert_1', 'Wert_4'])
                    new_row_z0b.dropna(inplace=True)
                    Error_dict['Z0B'].dropna(inplace=True)
                    if not new_row_z0b.empty and not new_row_z0b.isna().all().all():
                        Error_dict['Z0B'] = pd.concat([Error_dict['Z0B'], new_row_z0b], ignore_index=True)
            else:
                print("Missing Z0B at cycle: ", keys)
            # ------------------------------------------------------------------------------------------
            # A0B calculation
            #search indices where 'Antastrichtung' is Y and 'B Axis position' is 0, 180
            if len(indices_Y0C) == 4: #check if Y0C is complete else not possible to calculate A0B
                d = 10/1000 #diameter in mm
                indices1_A0B = cycles[keys].loc[(cycles[keys]['Antastrichtung'] == 'Y') & (cycles[keys]['B Axis position'] == 90)].index.tolist()
                indices2_A0B = cycles[keys].loc[(cycles[keys]['Antastrichtung'] == 'Y') & (cycles[keys]['B Axis position'] == 270)].index.tolist()
                if indices1_A0B and indices2_A0B:
                    # extract rows
                    selected_rows1_A0B = cycles[keys].loc[indices1_A0B[0], ['X Axis position', 'Y Axis position']]
                    selected_rows2_A0B = cycles[keys].loc[indices2_A0B[0], ['X Axis position', 'Y Axis position']]
                    selected_rows1_A0B_time = cycles[keys].loc[indices1_A0B[0], ['Time']]
                    selected_rows2_A0B_time = cycles[keys].loc[indices2_A0B[0], ['Time']]
                    selected_rows1_A0B_time['Time'] = pd.to_datetime(selected_rows1_A0B_time['Time'])
                    selected_rows2_A0B_time['Time'] = pd.to_datetime(selected_rows2_A0B_time['Time'])
                    mean_time_rotated_y0c = selected_rows1_A0B_time['Time'] + (selected_rows2_A0B_time['Time'] - selected_rows1_A0B_time['Time']) / 2
                    delta_y_A0B = selected_rows2_A0B['Y Axis position']-selected_rows1_A0B['Y Axis position']
                    #if selected_rows1_A0B['Y Axis position'] > selected_rows2_A0B['Y Axis position']:
                    #    A0B = (-1)*delta_y_A0B/d
                    #else:
                    #    A0B = delta_y_A0B/d #in Y um/m
                    A0B = delta_y_A0B / d
                    #insert the value into the dictionary
                    new_row_A0B = pd.DataFrame([[mean_time_rotated_y0c, 'A0B', A0B]], columns=['Time', 'Wert_1', 'Wert_4'])
                    new_row_A0B.dropna(inplace=True)
                    Error_dict['A0B'].dropna(inplace=True)
                    if not new_row_A0B.empty and not new_row_A0B.isna().all().all():
                        Error_dict['A0B'] = pd.concat([Error_dict['A0B'], new_row_A0B], ignore_index=True)

            else:
                print("Missing A0B at cycle: ", keys)
            # ------------------------------------------------------------------------------------------
            # C0B calculation
            # search indices where 'Antastrichtung' is Y and 'B Axis position' is 90, 270
            if len(indices_Y0C) == 4:
                d = 10/1000 #diameter in mm
                indices1_C0B = cycles[keys].loc[(cycles[keys]['Antastrichtung'] == 'Y') & (cycles[keys]['B Axis position'] == 0)].index.tolist()
                indices2_C0B = cycles[keys].loc[(cycles[keys]['Antastrichtung'] == 'Y') & (cycles[keys]['B Axis position'] == 180)].index.tolist()
                if indices1_C0B and indices2_C0B:
                    # extract rows
                    selected_rows1_C0B = cycles[keys].loc[indices1_C0B[0], ['X Axis position', 'Y Axis position']]
                    selected_rows2_C0B = cycles[keys].loc[indices2_C0B[0], ['X Axis position', 'Y Axis position']]
                    selected_rows1_C0B_time = cycles[keys].loc[indices1_C0B[0], ['Time']]
                    selected_rows2_C0B_time = cycles[keys].loc[indices2_C0B[0], ['Time']]
                    selected_rows1_C0B_time['Time'] = pd.to_datetime(selected_rows1_C0B_time['Time'])
                    selected_rows2_C0B_time['Time'] = pd.to_datetime(selected_rows2_C0B_time['Time'])
                    mean_time_rotated_y0c = selected_rows1_C0B_time['Time'] + (selected_rows2_C0B_time['Time'] - selected_rows1_C0B_time['Time']) / 2
                    delta_y_C0B = selected_rows2_C0B['Y Axis position']-selected_rows1_C0B['Y Axis position']
                    #if selected_rows1_C0B['Y Axis position'] > selected_rows2_C0B['Y Axis position']:
                    #    C0B = (-1)*delta_y_C0B/d
                    #else:
                    #    C0B = delta_y_C0B/d
                    C0B = delta_y_C0B / d
                    # insert the value into the dictionary
                    new_row_C0B = pd.DataFrame([[mean_time_rotated_y0c, 'C0B', C0B]], columns=['Time', 'Wert_1', 'Wert_4'])
                    new_row_C0B.dropna(inplace=True)
                    Error_dict['C0B'].dropna(inplace=True)
                    if not new_row_C0B.empty and not new_row_C0B.isna().all().all():
                        Error_dict['C0B'] = pd.concat([Error_dict['C0B'], new_row_C0B], ignore_index=True)
            else:
                print("Missing C0B at cycle: ", keys)
            # ------------------------------------------------------------------------------------------
            # Rotated C Axis by 90°
            # ------------------------------------------------------------------------------------------
            # Rotated Y0B_2 by 90°
            # search indices where in column 'C Axis position' is 90 & 'Antastrichtung is 'X'
            indices_rotated_Y0C = cycles[keys].loc[(cycles[keys]['C Axis position'] == 90) & (cycles[keys]['Antastrichtung'] == 'X')].index.tolist()
            if indices_rotated_Y0C:
                if len(indices_rotated_Y0C) == 4:
                    cycles[keys].loc[indices_rotated_Y0C, 'B Axis position'] = [0, 90, 180, 270]
                # extract the rows
                selected_rows_rotated_Y0C = cycles[keys].loc[indices_rotated_Y0C[0]:indices_rotated_Y0C[-1], ['X Axis position', 'Y Axis position']]
                selected_rows_rotated_Y0C_time = cycles[keys].loc[indices_rotated_Y0C[0]:indices_rotated_Y0C[-1], ['Time']]
                # calculate the mean of the selected rows
                mean_selected_rows_rotated_Y0C = selected_rows_rotated_Y0C.mean()
                selected_rows_rotated_Y0C_time['Time'] = pd.to_datetime(selected_rows_rotated_Y0C_time['Time'])
                mean_time_rotated_y0c = selected_rows_rotated_Y0C_time['Time'].min() + (selected_rows_rotated_Y0C_time['Time'].max() - selected_rows_rotated_Y0C_time['Time'].min()) / 2
                # insert the value into the dictionary
                new_row_rotated_y0c = pd.DataFrame([[mean_time_rotated_y0c, 'Y0B_2', mean_selected_rows_rotated_Y0C['X Axis position']]],columns=['Time', 'Wert_1', 'Wert_4'])
                new_row_rotated_y0c.dropna(inplace=True)
                Error_dict['Y0B_2'].dropna(inplace=True)
                if not new_row_rotated_y0c.empty and not new_row_rotated_y0c.isna().all().all():
                    Error_dict['Y0B_2'] = pd.concat([Error_dict['Y0B_2'], new_row_rotated_y0c], ignore_index=True)
            else:
                print("Missing Y0B_2 at cycle: ", keys)
            # ------------------------------------------------------------------------------------------
            # Rotated X0B_2 by 90°
            # search indices where in column 'C Axis position' is 90 & 'Antastrichtung is 'Y'
            indices_rotated_X0B = cycles[keys].loc[(cycles[keys]['C Axis position'] == 90) & (cycles[keys]['Antastrichtung'] == 'Y')].index.tolist()
            if indices_rotated_X0B:
                # extract the rows
                selected_rows_rotated_X0B = cycles[keys].loc[indices_rotated_X0B[0]:indices_rotated_X0B[-1], ['X Axis position', 'Y Axis position']]
                selected_rows_rotated_X0B_time = cycles[keys].loc[indices_rotated_X0B[0]:indices_rotated_X0B[-1], ['Time']]
                # calculate the mean of the selected rows
                mean_selected_rows_rotated_X0B = selected_rows_rotated_X0B.mean()
                selected_rows_rotated_X0B_time['Time'] = pd.to_datetime(selected_rows_rotated_X0B_time['Time'])
                mean_time_rotated_x0b = selected_rows_rotated_X0B_time['Time'].min() + (selected_rows_rotated_X0B_time['Time'].max() - selected_rows_rotated_X0B_time['Time'].min()) / 2
                # insert the value into the dictionary
                new_row_rotated_x0b = pd.DataFrame([[mean_time_rotated_x0b, 'X0B_2', mean_selected_rows_rotated_X0B['Y Axis position']]],columns=['Time', 'Wert_1', 'Wert_4'])
                new_row_rotated_x0b.dropna(inplace=True)
                Error_dict['X0B_2'].dropna(inplace=True)
                if not new_row_rotated_x0b.empty and not new_row_rotated_x0b.isna().all().all():
                    Error_dict['X0B_2'] = pd.concat([Error_dict['X0B_2'], new_row_rotated_x0b], ignore_index=True)
            else:
                print("Missing X0B_2 at cycle: ", keys)
            # ------------------------------------------------------------------------------------------
            # A0B_90 calculation
            if len(indices_rotated_Y0C) == 4:
                d = 10/1000
                indices1_A0B_90 = cycles[keys].loc[(cycles[keys]['Antastrichtung'] == 'X') & (cycles[keys]['B Axis position'] == 90)].index.tolist()
                indices2_A0B_90 = cycles[keys].loc[(cycles[keys]['Antastrichtung'] == 'X') & (cycles[keys]['B Axis position'] == 270)].index.tolist()
                if indices1_A0B_90 and indices2_A0B_90:
                    # extract rows
                    selected_rows1_A0B_90 = cycles[keys].loc[indices1_A0B_90[0], ['X Axis position', 'Y Axis position']]
                    selected_rows2_A0B_90 = cycles[keys].loc[indices2_A0B_90[0], ['X Axis position', 'Y Axis position']]
                    selected_rows1_A0B_90_time = cycles[keys].loc[indices1_A0B_90[0], ['Time']]
                    selected_rows2_A0B_90_time = cycles[keys].loc[indices2_A0B_90[0], ['Time']]
                    selected_rows1_A0B_90_time['Time'] = pd.to_datetime(selected_rows1_A0B_90_time['Time'])
                    selected_rows2_A0B_90_time['Time'] = pd.to_datetime(selected_rows2_A0B_90_time['Time'])
                    mean_time_rotated_y0c = selected_rows1_A0B_90_time['Time'] + (selected_rows2_A0B_90_time['Time'] - selected_rows1_A0B_90_time['Time']) / 2
                    delta_y_A0B_90 = selected_rows2_A0B_90['X Axis position'] - selected_rows1_A0B_90['X Axis position']
                    #if selected_rows1_A0B_90['X Axis position'] > selected_rows2_A0B_90['X Axis position']:
                    #    A0B_90 = (-1)*delta_y_A0B_90/d
                    #else:
                    #    A0B_90 = delta_y_A0B_90/d
                    A0B_90 = (-1)*delta_y_A0B_90 / d
                    # insert the value into the dictionary
                    new_row_A0B_90 = pd.DataFrame([[mean_time_rotated_y0c, 'A0B_90', A0B_90]], columns=['Time', 'Wert_1', 'Wert_4'])
                    new_row_A0B_90.dropna(inplace=True)
                    Error_dict['A0B_90'].dropna(inplace=True)
                    if not new_row_A0B_90.empty and not new_row_A0B_90.isna().all().all():
                        Error_dict['A0B_90'] = pd.concat([Error_dict['A0B_90'], new_row_A0B_90], ignore_index=True)
            else:
                print("Missing A0B_90 at cycle: ", keys)
            # ------------------------------------------------------------------------------------------
            # C0B_90 calculation
            if len(indices_rotated_Y0C) == 4:
                d = 10/1000
                indices1_C0B_90 = cycles[keys].loc[(cycles[keys]['Antastrichtung'] == 'X') & (cycles[keys]['B Axis position'] == 0)].index.tolist()
                indices2_C0B_90 = cycles[keys].loc[(cycles[keys]['Antastrichtung'] == 'X') & (cycles[keys]['B Axis position'] == 180)].index.tolist()
                if indices1_C0B_90 and indices2_C0B_90:
                    # extract rows
                    selected_rows1_C0B_90 = cycles[keys].loc[indices1_C0B_90[0], ['X Axis position', 'Y Axis position']]
                    selected_rows2_C0B_90 = cycles[keys].loc[indices2_C0B_90[0], ['X Axis position', 'Y Axis position']]
                    selected_rows1_C0B_90_time = cycles[keys].loc[indices1_C0B_90[0], ['Time']]
                    selected_rows2_C0B_90_time = cycles[keys].loc[indices2_C0B_90[0], ['Time']]
                    selected_rows1_C0B_90_time['Time'] = pd.to_datetime(selected_rows1_C0B_90_time['Time'])
                    selected_rows2_C0B_90_time['Time'] = pd.to_datetime(selected_rows2_C0B_90_time['Time'])
                    mean_time_rotated_y0c = selected_rows1_C0B_90_time['Time'] + (selected_rows2_C0B_90_time['Time'] - selected_rows1_C0B_90_time['Time']) / 2
                    delta_y_C0B_90 = selected_rows2_C0B_90['X Axis position'] - selected_rows1_C0B_90['X Axis position']
                    #if selected_rows1_C0B_90['X Axis position'] > selected_rows2_C0B_90['X Axis position']:
                    #    C0B_90 = (-1)*delta_y_C0B_90/d
                    #else:
                    C0B_90 = (-1)*delta_y_C0B_90/d
                    # insert the value into the dictionary
                    new_row_C0B_90 = pd.DataFrame([[mean_time_rotated_y0c, 'C0B_90', C0B_90]], columns=['Time', 'Wert_1', 'Wert_4'])
                    new_row_C0B_90.dropna(inplace=True)
                    Error_dict['C0B_90'].dropna(inplace=True)
                    if not new_row_C0B_90.empty and not new_row_C0B_90.isna().all().all():
                        Error_dict['C0B_90'] = pd.concat([Error_dict['C0B_90'], new_row_C0B_90], ignore_index=True)
            else:
                print("Missing C0B_90 at cycle: ", keys)

        # Create a list of indices
        """
        indices = list(range(len(list_phi2)))
        plt.figure(figsize=(10, 6))
        plt.plot(indices, list_phi2, marker='o')
        plt.title('Plot of list_phi2')
        plt.xlabel('Indices')
        plt.ylabel('Values')
        plt.grid(True)
        plt.show()
        """
        # Assuming list_XZ0B2 is your list of measurements

        # Formula for calculating the standard deviation
        #std_dev = np.std(Error_dict['X0B']['Wert_4'])
        #print("The standard deviation is:", std_dev)

        #Calculate the difference before and after 90° rotation
        #Delta Y0B = Y0B_2 - Y0B Y0C
        #Error_dict['Y0C'] = Error_dict['Y0B_2'].copy()
        Error_dict['Y0C']['Wert_4'] = Error_dict['Y0B_2']['Wert_4'] - Error_dict['Y0B']['Wert_4']
        Error_dict['Y0C']['Wert_1'] = 'Y0C'
        #mean of Time in Error_dict['Y0B_2']['Time'] and Error_dict['Y0B']['Time']
        Error_dict['Y0C']['Time'] = Error_dict['Y0B']['Time'] + (Error_dict['Y0B_2']['Time']-Error_dict['Y0B']['Time'])/2

        #------------------------------------------------------------------------------------------
        #Delta X0B = X0B_2 - X0B X0C
        Error_dict['X0B_2']['Time'] = pd.to_datetime(Error_dict['X0B_2']['Time'])
        Error_dict['X0B']['Time'] = pd.to_datetime(Error_dict['X0B']['Time'])
        # Step 2: Merge on 'Time' with a tolerance of 1 minute
        df_temp = Error_dict['X0B'].sort_values('Time').copy()
        df_temp['Original_Time'] = df_temp['Time']
        # Perform the merge
        merged_df = pd.merge_asof(Error_dict['X0B_2'].sort_values('Time'), df_temp, on='Time', tolerance=pd.Timedelta(minutes=3), direction='nearest')
        #merged2_df = pd.merge_asof(Error_dict['X0B_2'].sort_values('Time'), Error_dict['X0B'].sort_values('Time'),on='Time', tolerance=pd.Timedelta(minutes=1), direction='nearest')
        merged_df['Wert_4_diff'] = merged_df['Wert_4_x'] - merged_df['Wert_4_y']

        Error_dict['X0C']['Wert_4'] = merged_df['Wert_4_diff']
        Error_dict['X0C']['Wert_1'] = 'X0C'
        Error_dict['X0C']['Time'] = merged_df['Original_Time'] + (merged_df['Time'] - merged_df['Original_Time']) / 2
        del(merged_df)
        # ------------------------------------------------------------------------------------------
        # Winkelfehler berechnen

        # Delta A0B = A0B_90 - A0B
        # Convert 'Time' to datetime
        Error_dict['A0B_90']['Time'] = pd.to_datetime(Error_dict['A0B_90']['Time'])
        Error_dict['A0B']['Time'] = pd.to_datetime(Error_dict['A0B']['Time'])
        # Determine which dataframe is smaller
        if len(Error_dict['A0B_90']) < len(Error_dict['A0B']):
            smaller_df = Error_dict['A0B_90'].sort_values('Time')
            larger_df = Error_dict['A0B'].sort_values('Time')
        else:
            smaller_df = Error_dict['A0B'].sort_values('Time')
            larger_df = Error_dict['A0B_90'].sort_values('Time')
        # Create a copy of the larger dataframe and add 'Original_Time' column
        df_temp = larger_df.copy()
        df_temp['Original_Time'] = df_temp['Time']
        # Perform the merge
        merged_df = pd.merge_asof(smaller_df, df_temp, on='Time', tolerance=pd.Timedelta(minutes=3),direction='nearest')
        # Calculate 'Wert_4_mean'
        #merged_df['Wert_4_x'] = merged_df['Wert_4_x'] - merged_df['Wert_4_x'][0]
        #merged_df['Wert_4_y'] = merged_df['Wert_4_y'] - merged_df['Wert_4_y'][0]
        merged_df['Wert_4_mean'] = (merged_df['Wert_4_x'] + merged_df['Wert_4_y']) / 2
        #merged_df = merged_df.dropna()
        # Update Error_dict['A0B']
        #Error_dict['A0B'] = Error_dict['A0B_90'].copy()
        Error_dict['A0B']['Wert_1'] = 'A0B'
        Error_dict['A0B']['Wert_4'] = merged_df['Wert_4_mean']
        Error_dict['A0B']['Time'] = merged_df['Original_Time'] + (merged_df['Time'] - merged_df['Original_Time']) / 2
        #Error_dict['A0B'] = Error_dict['A0B'].dropna()
        # Delete merged_df
        del (merged_df)

        # Convert 'Time' to datetime
        Error_dict['C0B_90']['Time'] = pd.to_datetime(Error_dict['C0B_90']['Time'])
        Error_dict['C0B']['Time'] = pd.to_datetime(Error_dict['C0B']['Time'])
        # Determine which dataframe is smaller
        if len(Error_dict['C0B_90']) < len(Error_dict['C0B']):
            smaller_df = Error_dict['C0B_90'].sort_values('Time')
            larger_df = Error_dict['C0B'].sort_values('Time')
        else:
            smaller_df = Error_dict['C0B'].sort_values('Time')
            larger_df = Error_dict['C0B_90'].sort_values('Time')
        # Create a copy of the larger dataframe and add 'Original_Time' column
        df_temp = larger_df.copy()
        df_temp['Original_Time'] = df_temp['Time']
        # Perform the merge
        merged_df = pd.merge_asof(smaller_df, df_temp, on='Time', tolerance=pd.Timedelta(minutes=3), direction='nearest')
        # Calculate 'Wert_4_mean'
        merged_df['Wert_4_mean'] = (merged_df['Wert_4_x'] + merged_df['Wert_4_y']) / 2
        # Update Error_dict['C0B']
        Error_dict['C0B']['Wert_1'] = 'C0B'
        Error_dict['C0B']['Wert_4'] = merged_df['Wert_4_mean']
        Error_dict['C0B']['Time'] = merged_df['Original_Time'] + (merged_df['Time'] - merged_df['Original_Time']) / 2
        Error_dict['C0B'] = Error_dict['C0B'].dropna()
        # Delete merged_df
        del (merged_df)

        # ------------------------------------------------------------------------------------------
        #Nullen der Werte
        keys_to_delete = ['X0B_2', 'Y0B_2', 'A0B_90', 'C0B_90', 'A0B', 'C0B']
        for key in keys_to_delete:
            if key in Error_dict:
                del Error_dict[key]

        #calculate the reference values and store it into reference_dict
        for keys in Error_dict.keys():
            first_value = Error_dict[keys]['Wert_4'].iloc[0]  # Get the first value of Wert_4 column
            # Subtract the first value from all values in Wert_4 column
            Error_dict[keys]['Wert_4'] -= first_value  # mit referenz zu Nullpunkt
            reference_dict[keys] = pd.DataFrame({'Time': [Error_dict[keys].iloc[0, 0]], 'Wert_1': [Error_dict[keys].iloc[0, 1]], 'Wert_4': [first_value]})
        #------------------------------------------------------------------------------------------
        #Werte plotten
        #plot the data
        #fig, axs = plt.subplots(len(Error_dict), 1, figsize=(10, 10))

        #for (key, ax) in zip(Error_dict.keys(), axs.flatten()):
        #    Error_dict[key].plot(x='Time', y='Wert_4', title=key, legend=False, ax=ax)
        #    ax.grid(True)

        #plt.tight_layout()
        #plt.show()
        #plt.savefig(r'C:\Users\mzorzini\OneDrive - ETH Zurich\Zorzini_Inspire\Semester_Project\Weekly\Weekly 9\Bilder\Error_Calc\Error_Values.png', dpi=300)
        #plt.close()
        """ 
        color_dict = {
            'X0B': 'red',
            'Y0B': 'green',
            'Z0B': 'blue',
            'X0C': 'darkred',
            'Y0C': 'darkgreen',
            'A0B': 'red',
            'C0B': 'blue'
        }

        for key in Error_dict.keys():
            # Convert 'Time' to datetime if it's not already
            Error_dict[key]['Time'] = pd.to_datetime(Error_dict[key]['Time'])

            # Subtract the first time value from the entire 'Time' column and convert to hours
            Error_dict[key]['Time'] = (Error_dict[key]['Time'] - Error_dict[key]['Time'].iloc[
                0]).dt.total_seconds() / 3600

            fig, ax = plt.subplots(figsize=(10, 5))
            Error_dict[key].plot(x='Time', y='Wert_4', legend=False, ax=ax, linewidth=2,
                                 color=color_dict.get(key, 'black'))
            ax.grid(True)

            # Set title with fontsize 18
            ax.set_title(f'Thermal Error $E_{{{key}}}$', fontsize=18)

            # Set x-axis label
            ax.set_xlabel('Time [h]', fontsize=16)

            # Set y-axis label based on key
            if key in ['A0B', 'C0B']:
                ax.set_ylabel('Thermal Error [μm/m]', fontsize=16)
            else:
                ax.set_ylabel('Thermal Error [μm]', fontsize=16)

            # Set tick size
            ax.tick_params(axis='both', which='major', labelsize=16)

            plt.tight_layout()
            plt.show()
            plt.savefig(
                f'C:\\Users\\mzorzini\\OneDrive - ETH Zurich\\Zorzini_Inspire\\Semester_Project\\Weekly\\Weekly 10\\Bilder\\Error_Calc\\{key}_Error_Values.png',
                dpi=300)
            plt.close()
        """
        #------------------------------------------------------------------------------------------
        #return data
        #return data_error_1, start_iso, end_iso, reference_Dataframe
        #drop duplicates in each dictionary, else sampling would have problem
        for key in Error_dict.keys():
            original_length = len(Error_dict[key])
            Error_dict[key] = Error_dict[key].drop_duplicates(subset='Time', keep='first')
            Error_dict[key] = Error_dict[key].dropna(subset=['Time'])
            new_length = len(Error_dict[key])
            if original_length != new_length:
                print(f"Rows removed (either duplicates or NaT) in {key} at time {Error_dict[key]['Time'].iloc[-1]}")
            Error_dict[key] = Error_dict[key].reset_index(drop=True)

        print("Thermal Error Calculation Finished")
        return Error_dict, reference_dict






