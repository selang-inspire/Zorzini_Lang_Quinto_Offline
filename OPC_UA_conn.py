# OPCUA connection object
import time, datetime
import sched
import numpy as np
import pandas as pd
from threading import Thread, Event
import sys
import os, csv
import pytz
from pathlib import Path
from opcua import Client
from opcua import ua
from influx_data_loading import influx_export
from Class_Kinematic import errorMeasurement

class OPCUAcon(Thread):
    """"Parameters
    ----------
    configuration_id: selects configuration from self.master_conf dictionary for Tuning:
    "5" = GB, "6" = GC, "7" = GX, "8" = GY, "99" = Teststand
    machine_id: Agathon machine id
    connection_id: Network id for OPC UA server
    server_port: Port of the OPC UA server
    """

    def __init__(self,measurementFrequency,log_file_name,LogInfluxFrequency, machine_id=163, connection_id="192.168.250.3", server_port="4840"):
        Thread.__init__(self)
        self.__flag = Event()  # The flag used to pause the thread
        self.__flag.set()  # Set to True
        self.__running = Event()  # Used to stop the thread identification
        self.__running.set()  # Set running to True
        self.argv = sys.argv
        self.exectutable = sys.executable

        self.master_conf = {"0": {'sercosIP': '192.168.143.12,0,0', #access for example by list(master_conf.values())[0]["sercosIP"]
                                  'axis_name': 'GA',#TODO Check all names G A verified
                                  },
                            "1": {'sercosIP': '192.168.143.9,0,0', #G S Drive (Schleifspindel)
                                  'axis_name': 'GS1',
                                  },
                            "2": {'sercosIP': '192.168.143.9,1,0', #G Y Drive
                                  'axis_name': 'GS1_2',
                                  },
                            "3": {'sercosIP': '192.168.143.10,0,0', #G S 2 Abrichtspindel
                                  'axis': 'GS2',
                                  },
                            "4": {'sercosIP': '192.168.143.10,1,0', # TODO something wrong, this should be G B but it is not
                                  'axis': 'GB',
                                  },
                            "5": {'sercosIP': '192.168.143.1,0,0',#G X not usable only switch behaviour usually 2°C
                                  'axis': 'GX',
                                  },
                            "6": {'sercosIP': '192.168.143.1,1,0',# TODO Should be G_C is not e.g. 25 instead of 2°C
                                  'axis': 'GC',
                                  },
                            "7": {'sercosIP': '192.168.143.15,0,0',# MB C r probalby C 2 achse
                                  'axis': 'GC_r',
                                  },
                            "8": {'sercosIP': '192.168.143.20,0,0',# G X probably bette X value
                                  'axis': 'GX_evo',
                                  },
                            "9": {'sercosIP': '192.168.143.21,0,0',# G Z evo location unknown, maybe lift for pallette Rohlinge?
                                  'axis': 'GZ_evo',
                                  },
                            "10": {'sercosIP': '192.168.143.22,0,0',# G U probably location of cleaning wheel in X?
                                  'axis': 'GU',
                                  },
                            "11": {'sercosIP': '192.168.143.22,1,0',# G U spindel TODO Verify adress
                                  'axis': 'GU_S',
                                  },
                            }
        self.OPCNames = ['A-drive','S-drive (grinding)','Y-drive','S2-drive (dress)','B-drive','X-drive','C-drive',
                         'C-drive rot','GX_evo','Z-drive (Pallette)','U-drive','US-drive'] #'A-drive','S-drive (grinding)','Y-drive','S2-drive (dress)','B-drive (tocheck)','X-drive','C-drive (tocheck)', 'C-drive rot (tocheck)','GX_evo','Z-drive (Pallette)','U-drive','US-drive'
        self.MeasNames =  [axisname + " Temperature" for axisname in self.OPCNames] + [axisname + " Power" for axisname in self.OPCNames] + [axisname + " Energy" for axisname in self.OPCNames]
        self.node = []

        self.machine_id = machine_id
        self.connection_id = connection_id
        self.server_port = server_port
        self.measurementFrequency = measurementFrequency #Measurement frequency in seconds for drives and other recorded values TODO smarter than sleep duration
        self.LogInfluxFrequency = LogInfluxFrequency #Log frequency in seconds for influxdb
        self.timezone = pytz.timezone('Europe/Zurich') #Check if this is the right timezone for international use. Maybe from system time?
        self.timestamp_initialization = datetime.datetime.now(self.timezone)
        self.previousTime    = datetime.datetime.combine(datetime.date.min, datetime.time.min, self.timezone)

        self.connection = None # OPC UA connection
        self.config = None
        self.con_ready = False # Flag determines if connection works and conditions, that have to be set manually by the operator are ok
        self.set_ready = False # Flag determines if configuration parameters are set
        self.ObserveTouchProbe = False #Flag determines if touch probe WMES observation is active TODO

        self.Measurement = []
        self.DriveTemp = np.empty(len(self.master_conf))
        self.DrivePower = np.empty(len(self.master_conf))
        self.DriveEnergy = np.empty(len(self.master_conf))

        self.SaveasCSV = True
        self.SaveasInflux = True
        self.ServerInflux = "WS16" #Local or WS16(Cloud at ETH) Local not yet implemented 
        self.PrintMeasurements = True
        self.log_file_name = log_file_name
        self.argv = sys.argv
        self.executable = sys.executable

        #WMES Setup for recording touch probe measurements
        self.WMES_Counter = -1 #Counter for WMES observations, if it increases a new measurement was carried through. Increase triggers latch recording
        self.WMES_node = []
        self.WMES_Node_main_Name = "ns=2;s=.WMes_DATEN" #Node for WMES observation, followed by eg [15]
        self.WMES_Nodes_IDs =list(range(1,17))
        self.WMES_Meas = []


        self.init_logFile()  # Create a csv if it doesn't exist

    def __del__(self):
        self.unsubscribe()
        self.client.disconnect()

    def unsubscribe(self):
        if self.sub:
            self.sub.delete()
            self.sub = None

    def pause(self):
        self.__flag.clear()  # Set to False to block the thread

    def resume(self):
        self.__flag.set()  # Set to True, let the thread stop blocking

    def stop(self):
        self.__flag.set()  # Resume the thread from the suspended state, if it is already suspended
        self.__running.clear()  # Set to False

    def init_logFile(self):
        # Create the csv file for the rtd temperatures if it doesn't exist
        if self.SaveasCSV:
            if not (Path(os.getcwd()) / self.log_file_name).is_file():
                with open(self.log_file_name, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(['Date/Time'] + self.OPCNames)

    def datachange_notification (self, node, val,data):
        # Here you can call any function you want to handle the change
        # For example:
        if self.WMES_Counter>0:
            print(f"WMES change on {node}: New value: {val}")
            self.RecordTouchProbe()
        self.WMES_Counter = val

    def RecordTouchProbe(self):
        #Only the value of the touch probe latch in the moving axis is recorded, the rest of the data is not used or stored currently
        #The calculation of the DeltaX and DeltaY is done by checking the greater stop distance and not a clean solution
        #TODO Get measurements into the main file in a clean way
        def record():
            # This is the original RecordTouchProbe logic, moved into a separate thread
            datatmp = []
            for i in range(len(self.WMES_node)):
                try:
                    datatmp.append(self.WMES_node[i].get_value())
                except Exception as e:
                    print(f"Error reading node: {e}")
            DeltaX = datatmp[5] - datatmp[11]
            DeltaY = datatmp[6] - datatmp[12]
            if self.PrintMeasurements:
                print(datatmp)
            measurement_type = 'X' if abs(DeltaX) > abs(DeltaY) else 'Y'
            measurement_value = datatmp[5] if measurement_type == 'X' else datatmp[6]
            measurement_time = datetime.datetime.now(self.timezone).strftime("%Y-%m-%dT%H:%M:%S.%fZ")  # ISO 8601 format

            self.WMES_Meas.append({
                'time': measurement_time,
                'type': measurement_type,
                'value': measurement_value
            })
            self.Error_To_Influx_Counter += 1  
        # Launch the record function in a new thread
        record_thread = Thread(target=record)
        record_thread.start()
    def send_to_influx():
        if self.WMES_Meas:  # Checks if there are measurements to send
            influx_export(self.WMES_Meas, self.ServerInflux, self.MeasNames, self.timezone)
            self.WMES_Meas.clear()  # Clear the measurements after sending
        scheduler.enter(LogInfluxFrequency, 1, send_to_influx)  # Reschedule after LogInfluxFrequency / 10 seconds

    def ReadAxis(self):
        #GSX SercosIP,192.168.143.1,1,0”ParameterSet.“S-0-0383” (INT 16)  "SercosIP,192.168.143.12,0,0".ParameterSet."S-0-0383"
        #Zwischenkreisleistung
        #GA SercosIP,192.168.143.12,0,0”ParameterSet.“S-0-0382” (INT 16)
        for drive in range(int(len(self.node)/3)): #Careful hardcoded difference between drive temp and power (Zwischenkreisleistung), has to be adapted if extended
            self.DriveTemp[drive] = self.node[drive].get_value()/10
        for drive in range(int(len(self.node)/3)):
            self.DrivePower[drive] = self.node[drive+int(len(self.node)/3)].get_value()
        for drive in range(int(len(self.node)/3)):
            self.DriveEnergy[drive] = self.node[drive+int(len(self.node)/3*2)].get_value()

        #return self.DriveTemp probably not necessary as part of self?


    def writeData(self, t):
        if self.SaveasCSV:
            try:
                # Write the rtd temperatures
                with open(self.log_file_name, 'a', newline='') as csvfile:
                    writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    writer.writerows(t)
            except:
                print('Please, make sure that all .csv files are closed')

        if self.SaveasInflux:
            try:
                if self.Error_To_Influx_Counter > 0:
                    influx_export(t, self.ServerInflux,self.MeasNames,self.timezone)
                    self.Error_To_Influx_Counter = 0
                else:
                    influx_export(t, self.ServerInflux,self.MeasNames,self.timezone)
            except:
                print("Fail Write to influx, check internet connectivity")
                raise Exception('influx')
    def init_connection(self):
        """Initializes the connection with the OPC UA server, this has to be called first before measurements can be started"""
        # Set the client url
        try:
            self.connection = Client('opc.tcp://' + self.connection_id + ':' + self.server_port)
            self.connection.connect()
            print("Successfully initialized connection to OPC Server")
            self.set_ready = True
            #ToDo Test connection by reading every variable required? Potentially in different try
        except:
            print('Connection failed. Attempted to connect to client: ','opc.tcp://' + self.connection_id + ':' + self.server_port)
        #Connect nodes for drive temperatures to self, later reads all values from self.node in ReadAxis and subsequent logging operations
        for drive in range(len(self.master_conf)):
            try:
                    self.node.append(self.connection.get_node('ns=7;s="SercosIP,' + list(self.master_conf.values())[drive][
                        "sercosIP"] + '".ParameterSet."' + 'S-0-0383' + '"'))
            except:
                print('Failed to connect to Drive. Ensure they are active and the adress correct. Tried connecting to: '
                    +'ns=7;s="SercosIP,' + list(self.master_conf.values())[drive][
                    "sercosIP"] + '".ParameterSet."' + 'S-0-0383' + '"')
                raise #TODO Ensure that entire communication is restarted
        for drive in range(len(self.master_conf)):
            try: #Add +1 to self.node len? TODO CHECK
                    self.node.append(self.connection.get_node('ns=7;s="SercosIP,' + list(self.master_conf.values())[drive][
                        "sercosIP"] + '".ParameterSet."' + 'S-0-0382' + '"'))    #Parameter set to Zwischenkreisleistung TODO check other interesting parameters?
            except:
                print('Failed to connect to Drive. Ensure they are active and the adress correct. Tried connecting to: '
                    +'ns=7;s="SercosIP,' + list(self.master_conf.values())[drive][
                    "sercosIP"] + '".ParameterSet."' + 'S-0-0382' + '"')
                raise
        for drive in range(len(self.master_conf)):
            try: #Add +1 to self.node len? TODO CHECK
                    self.node.append(self.connection.get_node('ns=7;s="SercosIP,' + list(self.master_conf.values())[drive][
                        "sercosIP"] + '".ParameterSet."' + 'P-0-0851' + '"'))    #Parameter set to Zwischenkreisleistung TODO check other interesting parameters?
            except:
                print('Failed to connect to Drive. Ensure they are active and the adress correct. Tried connecting to: '
                    +'ns=7;s="SercosIP,' + list(self.master_conf.values())[drive][
                    "sercosIP"] + '".ParameterSet."' + 'P-0-0851' + '"')
                raise
        #Connect nodes for touch probe observation
        for wmesNode in range(len(self.WMES_Nodes_IDs)):
           try:
                   self.WMES_node.append(self.connection.get_node(self.WMES_Node_main_Name+'['+ str(self.WMES_Nodes_IDs[wmesNode]) +']'+ '"'))
           except:
               print('Failed to connect to WMES. Ensure they are active and the adress correct. Tried connecting to: '
                   +self.WMES_Node_main_Name+ str(self.WMES_Nodes_IDs[wmesNode]) + '"')
               raise #TODO Ensure that entire communication is restarted
        #Subscribe to WMES observation
        self.sub = self.connection.create_subscription(50, self) # 500 is the publishing interval in milliseconds
        self.sub.subscribe_data_change(self.connection.get_node(self.WMES_node[15-1]))   
        scheduler = sched.scheduler(time.time, time.sleep)
        # Start the scheduler
        scheduler.enter(self.LogInfluxFrequency, 1, self.send_to_influx)
        scheduler.run()

    def run(self):

        try:
            self.init_connection()
            print("Starting OPC Recording")
            while self.__running.isSet():
                self.__flag.wait()  # Return immediately when it is True, block until the internal flag is True when it is False
                currentTime = datetime.datetime.now(self.timezone)
                # Read the values
                if currentTime >= self.previousTime + datetime.timedelta(0, self.measurementFrequency):
                    self.ReadAxis()  # Read temperatures
                    self.Measurement.append([[currentTime.strftime("%d.%m.%Y %H:%M:%S.%f")], self.DriveTemp, self.DrivePower,self.DriveEnergy])  # Concatenate time and temperature information
                    if self.PrintMeasurements:
                        print(self.Measurement[-1])
                    # plt.plot(self.rtdTemperatures[0:len(self.rtdTemperatures)-1])
                    # plt.show()
                    self.writeData(self.Measurement[-1])  # Save to .csv or setting specific location
                    self.previousTime = currentTime
                # Reset previousTime
            self.error = 0
        # return error_detection
        except:
            print('Error raised while loading or exporting data')
            self.error = 1
            print("restarting")
            os.execv(self.executable, ["python"] + self.argv) #TODO Ensure restart here!!!
