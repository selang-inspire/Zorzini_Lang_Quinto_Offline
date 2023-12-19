import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
class MT:
    def __init__(self, Name, mode,measurementFrequency,log_file_name):
        #Import Machine specific package depending on which machine is used
        self.ModelActive = False #TODO make functional

        if Name == "EVO_Quinto":
            from Class_EVO_Quinto import EVO_Quinto
            self.Machine = EVO_Quinto(log_file_name)

        elif Name == "EVO_100":
            from Class_EVO_100 import EVO_100
            self.Machine = EVO_100()
        else:
            raise SystemExit('Error: Unknown Machine Specific Library currently implemented "EVO_Quinto", "EVO100" or .')

        #self.IP_Overwrite_File = "C:/Users/Admin.AGATHON-7OEU3S8/AppData/Local/Agathon_AG/IpInputOverwrite/IpInputOverwrite.txt"
        self.IP_Overwrite_File = "//192.168.250.1/IpInputOverwrite/IpInputOverwrite.txt"
        self.IP_Log_File   = "//192.168.250.1/Bins/IpInputLog4R.tmp"
        self.MachineName   = Name
        self.Mode          = mode
        self.IP_Comp_Values = pd.DataFrame(columns=["Time"])
        self.Prediction = pd.DataFrame(columns=["Time","X Offset LR","Y Offset LR","Z Offset LR"])

        if mode == "Sim":
            self.ThermalError = []
            self.Inputs = []
            self.LoadDataOffline()
            
        elif mode == "Compensation" or mode == "Log":
            self.ThermalError = []
            self.Inputs = []
            self.Machine.ConnectMachine(measurementFrequency)
            self.Machine.OPC.start()
        else:
            raise SystemExit('Error: Unknown Machine Mode, currently implemented "Sim", "Compensation" or "Log".')

        if self.ModelActive:
            self.Model = Model_initialize



        #Test Arbitrary prediction values:
        self.Prediction.loc[0,"Time"] = datetime.now()
        self.Prediction.loc[0,"X Offset LR"] = 0.005
        self.Prediction.loc[0,"Y Offset LR"] = 0.0075
        self.Prediction.loc[0,"Z Offset LR"] = 0.0025

        self.Compensation_To_Machine()

    def LoadDataOffline(self):
        # self.ThermalError, self.Inputs = load_DataMachine.OfflineFileData(machineSpec)
        a=1+1

    def Read_State_Interpreter(self):
        #Read previous status from IP
        logf = open(self.IP_Log_File,"r")
        IP_Params = logf.read()
        entries = IP_Params.split(";")
        # Create a list to hold the name-value pairs
        name_value_pairs = []
        # Process each entry
        for entry in entries:
            if "=" in entry:  # Check if the entry contains an '=' sign
                name, value = entry.split(" = ")
                name_value_pairs.append((name.strip(), value.strip()))
                if name == "\nXOffsCorr4LR":
                    Xnr = len(name_value_pairs)-1
        locnr = len(self.IP_Comp_Values)
        self.IP_Comp_Values.loc[locnr,"Time"] = datetime.now()
        self.IP_Comp_Values.loc[locnr,"X Offset LR"] = name_value_pairs[Xnr][1]        
        self.IP_Comp_Values.loc[locnr,"Y Offset LR"] = name_value_pairs[Xnr+1][1]        
        self.IP_Comp_Values.loc[locnr,"Z Offset LR"] = name_value_pairs[Xnr+2][1]        
        #TODO Incorporate anvil pivot values that make sens

    def Write_Interpreter_Overwrite(self):
        f = open(self.IP_Overwrite_File,"r+")
        contents = f.read() #Read all content, currently not used, contents new writes independent of old
        #Delete all content
        f.truncate(0)
        #Define ofsset to correct
        locnr = len(self.Prediction)-1
        X =  "\nXOffsCorr4LR = " + str(self.Prediction.loc[locnr,"X Offset LR"]) + " ;" +"\n"
        Y = "YOffsCorr4LR = " + str(self.Prediction.loc[locnr,"Y Offset LR"]) + " ;" +"\n"
        Z = "ZOffsCorr4LR = " + str(self.Prediction.loc[locnr,"Z Offset LR"]) + " ;" +"\n" 
        contents_new = X+Y+Z
        #Write Compensation TxT
        f.write(contents_new)
        f.close()


    def Compensation_To_Machine(self):
        #TODO IP input overwrite

        #Read Current Interpreter values and safe them and the time in IP_Comp_Values
        self.Read_State_Interpreter()
        #ReadTxt from overwrite file, which is subsequently modified
        self.Write_Interpreter_Overwrite()
        
