import pandas as pd
from threading import Thread, Event
import csv
import numpy as np
from datetime import datetime
from OPC_UA_conn import OPCUAcon
from pytz import timezone

#machine specific parameters
class EVO_Quinto:

    def __init__(self,log_file_name):
        self.SensorList = ['A axis Drive Structure', 'Air Workingspace', 'Air back', 'B Drive gearbox', 'B WerkstückSpanner links', 'B WerkstückSpanner rechts', 'B drive gap between gear', 'Bed behind machine left, axis enclosure', 'C Axis Cover', 'C axis Top Auf Spindelstock Mitte', 'C axis side down', 'C axis top prisma', 'Coolant Backflow', 'Env Machine Front', 'Env Machine back middle', 'Oil Backflow', 'Spindle Structure Front', 'Touch Probe Holder Spindle', 'X Drive middle top', 'X drive back down', 'X structure cast right', 'bed below front'] #'Spindle back left casting' auskommentiert da dieser Sensor fehlerhaft ist
        self.ErrorList = ['X0B'] #TODO Update to pivotes
        self.log_file_name = log_file_name
        #Influx access to Quinto
        self.token = "4MecLF8nQznwGWhGSPQhi6v_Y3dvyoHVqlUvF7JZqEDIZGWqvwdwQQBvZ-oEObwkpCjj4oHb8_uTFm8VmDSYvQ=="
        self.url = "http://isim-ws016.intern.ethz.ch:8086"
        self.org = 'ThermoComp'
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
    def Load_Excel_Error(self, excel_datei, start_time, end_time, model_noise):
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

        #add noise to the error data
        if model_noise == True:
            extracted_df['Wert_4'] = extracted_df['Wert_4']+np.random.normal(0, 0.01, extracted_df['Wert_4'].shape[0]) #add noise to the data

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

    def TableLayout(Temperature,SensorList, ThermalError, ErrorList):         #nice temperature dataframe layout
        SensorList = ['date','time'] + SensorList
        FirstMeas = Temperature.index.values[Temperature.iloc[:,0]==1].tolist()
        Temperature = Temperature.drop(range(0,FirstMeas[0]))
        Temperature = Temperature.drop(Temperature.columns[[0]],axis=1)
        Temperature.columns = SensorList
        
        ErrorList = ['time'] + ErrorList
        ThermalError.columns = ErrorList

        return Temperature, ThermalError

    def ThermalErrorCalculation(Dx,Latch,Reference):  #error calculation
        ThermalError = pd.DataFrame()
        
        #set time of thermal error as the last measurement taken (latch)
        ThermalError.insert(0,"time",Latch.iloc[1:,0])
        
        #calculation of thermal error
        ThermalError.insert(1,"error",-Dx.iloc[1:,1]-Reference+Latch.iloc[1:,1]) 
        ThermalError.iloc[:,1] = (ThermalError.iloc[0:,1] - ThermalError.iloc[0,1])*1000
            
        return ThermalError



