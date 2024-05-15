"""
Created 2024-03-09  11:32:26
@author: Mario Zorzini (mzorzini)
"""
import numpy as np
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
from pytz import timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision




class InfluxDBQuery: #TODO: Better Modularity for changing the InfluxDB according to machine data storage
    '''
    - This class is used to access the InfluxDB and query the data
    - The init contains the key information to access the InfluxDB, retrieved from the MT specific class
    - The Output is the raw data from the InfluxDB and can be used for further processing
    '''
    def __init__(self, token, url, org, queryName):
        self.token = token
        self.url = url
        self.org = org
        self.queryName = queryName

    def query(self, start_iso, end_iso):
        '''
        Read data from InfluxDB
        '''
        client = influxdb_client.InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org
        )
        query_api = client.query_api()

        #maybe add more filter like |> filter(fn: (r) => r["_field"] == "temperature")
        if start_iso == None or end_iso == None: #get measurement from last 5 minutes and use newest measurement
            query = f'from(bucket: "{self.queryName}")\
                    |> range(start: -5m)\
                    |> filter(fn: (r) => r["_measurement"] =~ /.*/)'
                    #|> last()'
        else: #get a range of measurements--> e.g. training data
            query = f'from(bucket: "{self.queryName}")\
                |> range(start: time(v: "{start_iso}"), stop: time(v:"{end_iso}"))\
                |> filter(fn: (r) => r["_measurement"] =~ /.*/)\
                |> yield(name: "mean")'

        result = query_api.query(org=self.org, query=query)

        max_len = max(len(table.records) for table in result)
        results = np.empty([len(result), max_len])
        time_res = []
        TempNames = []
        time_res_energy = []
        count = 0

        #if start_iso == None or end_iso == None: #TODO: For new data this procedere for time column necessary
        for table in result:
            if count == 6:
                for record in table.records:
                    time_res.append((record.get_field(), record.get_time()))
            if count == 3:
                for record in table.records:
                    time_res_energy.append((record.get_field(), record.get_time()))
            microcount = 0
            for record in table.records:
                if microcount == 0:
                    TempNames.append((record.get_field(), record.get_measurement())[1])
                results[count][microcount] = ((record.get_field(), record.get_value()))[1]
                microcount += 1
            count += 1

        return TempNames, time_res, time_res_energy, results


    def position_query(self, start_iso, end_iso):
        '''
        This is only valid for Quinto164
        '''
        client = influxdb_client.InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org
        )
        query_api = client.query_api()

        query_x = f'from(bucket: "{self.queryName}")\
            |> range(start: time(v: "{start_iso}"), stop: time(v:"{end_iso}"))\
            |> filter(fn: (r) => r["_measurement"] == "A Axis position" or r["_measurement"] == "B Axis position" or r["_measurement"] == "C Axis position" or r["_measurement"] == "MB Axis position" or r["_measurement"] == "X Axis position" or r["_measurement"] == "Y Axis position")\
            |> filter(fn: (r) => r["_field"] == "X")'

        query_y = f'from(bucket: "{self.queryName}")\
                    |> range(start: time(v: "{start_iso}"), stop: time(v:"{end_iso}"))\
                    |> filter(fn: (r) => r["_measurement"] == "A Axis position" or r["_measurement"] == "B Axis position" or r["_measurement"] == "C Axis position" or r["_measurement"] == "MB Axis position" or r["_measurement"] == "X Axis position" or r["_measurement"] == "Y Axis position")\
                    |> filter(fn: (r) => r["_field"] == "Y")'

        result_x = query_api.query(org=self.org, query=query_x)
        result_y = query_api.query(org=self.org, query=query_y)

        max_len_x = max(len(table.records) for table in result_x)
        results_x = np.empty([len(result_x), max_len_x])
        time_res_x = []
        PosNames_x = []
        count_x = 0

        max_len_y = max(len(table.records) for table in result_y)
        results_y = np.empty([len(result_y), max_len_y])
        time_res_y = []
        PosNames_y = []
        count_y = 0

        for table in result_x:
            if count_x == 0:
                for record in table.records:
                    time_res_x.append((record.get_field(), record.get_time()))
            microcount = 0
            for record in table.records:
                if microcount == 0:
                    PosNames_x.append((record.get_field(), record.get_measurement())[1])
                results_x[count_x][microcount] = ((record.get_field(), record.get_value()))[1]
                microcount += 1
            count_x += 1

        for table in result_y:
            if count_y == 0:
                for record in table.records:
                    time_res_y.append((record.get_field(), record.get_time()))
            microcount = 0
            for record in table.records:
                if microcount == 0:
                    PosNames_y.append((record.get_field(), record.get_measurement())[1])
                results_y[count_y][microcount] = ((record.get_field(), record.get_value()))[1]
                microcount += 1
            count_y += 1

        return PosNames_x, time_res_x, results_x, PosNames_y, time_res_y, results_y

    def Load_ISO_Time(self, start_time, end_time):

        start = start_time  # "03/18/2024 04:10:00.00 PM"#extracted_df.iloc[0, 0]
        end = end_time  # "03/19/2024 10:59:59.00 AM"#extracted_df.iloc[-1, 0]

        #############Start UTC conversion
        # Define the Swiss timezone #TODO check if conversion necessary, else set influx server timezone?
        swiss_tz = timezone('Europe/Zurich')
        # Localize the datetime to Swiss time
        start_datetime_1 = swiss_tz.localize(datetime.strptime(start, "%m/%d/%Y %I:%M:%S.%f %p"))
        end_datetime_1 = swiss_tz.localize(datetime.strptime(end, "%m/%d/%Y %I:%M:%S.%f %p"))

        start_datetime_UTC = start_datetime_1.astimezone(timezone('UTC'))
        end_datetime_UTC = end_datetime_1.astimezone(timezone('UTC'))

        start_iso = start_datetime_UTC.strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ")  # for influxdb to extract corresponding temp data
        end_iso = end_datetime_UTC.strftime("%Y-%m-%dT%H:%M:%S.%fZ")  # for influxdb to extract corresponding temp data

        return start_iso, end_iso

    def influx_export_Prediction(self, value): #TODO: More in a general structure
        '''
        - This def is used to export the data to the InfluxDB
        '''
        try:
            if value is None:
                raise Exception('value is None')
            zurich_timezone = timezone('Europe/Zurich')
            # creating the client object
            client = influxdb_client.InfluxDBClient(url=self.url, token=self.token, org=self.org)
            bucket = "Agathon_Model"
            # writing the data into the database
            write_api = client.write_api(write_options=SYNCHRONOUS)
            DictionaryNames = list(value.keys())
            wert_4_values = []
            Time_values = []
            for key in value.keys():
                df = value[key]
                if 'Wert_4' in df.columns:
                    wert_4_values.extend(df['Wert_4'].tolist())
                if 'Time' in df.columns:
                    Time_values.extend(df['Time'].tolist())
            Upload_Values = wert_4_values
            Upload_Time = Time_values
            for i in range(len(DictionaryNames)):
                point = (
                    Point(DictionaryNames[i])
                    .field("Error", Upload_Values[i])  # value[i+1] because the first value is the time
                    .time(zurich_timezone.localize(datetime.now()))
                )
                write_api.write(bucket, self.org, point)
        except:
            raise Exception('error arised while exporting to influx')

    def influx_export_Inputs(self, column_names, first_row_values, key):  # TODO: More in a general structure
        '''
        - This def is used to export the data to the InfluxDB
        '''
        try:
            if first_row_values is None:  # Todo Switch between Temp and ThermalError
                raise Exception('value is None')

            zurich_timezone = timezone('Europe/Zurich')

            # creating the client object
            client = influxdb_client.InfluxDBClient(url=self.url, token=self.token, org=self.org)

            bucket = "Agathon_Model"

            # writing the data into the database
            write_api = client.write_api(write_options=SYNCHRONOUS)

            for i in range(len(column_names) - 1):
                # Ensure first_row_values[0] is a string
                if isinstance(first_row_values[0], float):
                    first_row_values[0] = str(first_row_values[0])

                point = (
                    Point(key)
                    .field(f"Inputs_{column_names[i + 1]}",
                           first_row_values[i + 1])  # Use a naming convention to indicate the association
                    .time(zurich_timezone.localize(datetime.now()))
                )
                write_api.write(bucket, self.org, point)
        except:
            raise Exception('error arised while exporting to influx')



