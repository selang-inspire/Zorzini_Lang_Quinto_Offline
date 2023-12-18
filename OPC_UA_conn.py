# OPCUA connection object
import time, datetime
import numpy as np
import pandas as pd
from threading import Thread, Event
import sys
import os, csv
from pathlib import Path
from opcua import Client
from opcua import ua


class OPCUAcon(Thread):
    """"Parameters
    ----------
    configuration_id: selects configuration from self.master_conf dictionary for Tuning:
    "5" = GB, "6" = GC, "7" = GX, "8" = GY, "99" = Teststand
    machine_id: Agathon machine id
    connection_id: Network id for OPC UA server
    server_port: Port of the OPC UA server
    """

    def __init__(self,measurementFrequency, machine_id=163, connection_id="192.168.250.3", server_port="4840"):
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
        self.OPCNames = ['Channel 1','Channel 2','Channel 3','Channel 4','Channel 5','Channel 6','Channel 7','Channel 8'] #TODO Adapt to actual measurements
        self.node = []

        self.machine_id = machine_id
        self.connection_id = connection_id
        self.server_port = server_port
        self.measurementFrequency = measurementFrequency #Measurement frequency in seconds for drives and other recorded values TODO smarter than sleep duration
        self.timestamp_initialization = datetime.datetime.now()
        self.previousTime    = datetime.datetime.combine(datetime.date.min, datetime.time.min)

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
        self.SaveasInflux = False
        self.PrintMeasurements = True
        self.log_file_name = "C:\\Users\\Admin.AGATHON-7OEU3S8\\Desktop\\MainThermokompensation\\Messdaten\\TP_Log_12_12_2023.csv" #TODO Move to main file and use nice folder structure

        self.argv = sys.argv
        self.executable = sys.executable

        self.init_logFile()  # Create a csv if it doesn't exist


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


    def Listener(self):
        #Records measurements and saves them TODO
        1*1

    def ReadAxis(self):
        #GSX SercosIP,192.168.143.1,1,0”ParameterSet.“S-0-0383” (INT 16)  "SercosIP,192.168.143.12,0,0".ParameterSet."S-0-0383"
        #Zwischenkreisleistung
        #GA SercosIP,192.168.143.12,0,0”ParameterSet.“S-0-0382” (INT 16)
        for drive in range(int(len(self.node)/3)): #Careful hardcoded difference between drive temp and power (Zwischenkreisleistung), has to be adapted if extended
            self.DriveTemp[drive] = self.node[drive].get_value() 
        for drive in range(int(len(self.node)/3)):
            self.DrivePower[drive] = self.node[drive+int(len(self.node)/3)].get_value()
        for drive in range(int(len(self.node)/3)):
            self.DriveEnergy[drive] = self.node[drive+int(len(self.node)/3*2)].get_value()

        #return self.DriveTemp probably not necessary as part of self?
    def MonitorTouchProbe(self):
        #TODO always active once called (Shutoff required?)
        # Monitor changes in touch probe and when registered record wmes value and assign it to the correct measurement step
        #TODO Adapt measurements depending on setable/callable measurement cycle --> Error calculation
        1*1

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
                Influx.influx_export(t, self.ServerInflux)
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

    def run(self):

        try:
            self.init_connection()
            print("Starting OPC Recording")
            while self.__running.isSet():
                self.__flag.wait()  # Return immediately when it is True, block until the internal flag is True when it is False
                currentTime = datetime.datetime.now()
                # Read the values
                if currentTime >= self.previousTime + datetime.timedelta(0, self.measurementFrequency):
                    self.ReadAxis()  # Read temperatures
                    self.Measurement.append([[currentTime.strftime("%d.%m.%Y %H:%M:%S.%f")], self.DriveTemp, self.DrivePower,self.DriveEnergy])  # Concatenate time and temperature information
                    if self.PrintMeasurements:
                        print(self.Measurement[-1])
                    # plt.plot(self.rtdTemperatures[0:len(self.rtdTemperatures)-1])
                    # plt.show()
                    self.writeData(self.Measurement[-1])  # Save to .csv or setting specific location
                    self.previousTime = datetime.datetime.now()
                # Reset previousTime
            self.error = 0
        # return error_detection
        except:
            print('Error raised while loading or exporting data')
            self.error = 1
            print("restarting")
            os.execv(self.executable, ["python"] + self.argv) #TODO Ensure restart here!!!
