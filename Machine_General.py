import re
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

        self.IP_Overwrite_File = "C:/Users/sebat/OneDrive - ETH Zurich/PHD/projekte/Agathon/Maschine/Kommunikation/IP_Write_Test.txt"
        self.MachineName  = Name
        self.Mode         = mode

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
    
    def LoadDataOffline(self):
        # self.ThermalError, self.Inputs = load_DataMachine.OfflineFileData(machineSpec)
        a=1+1
            

    def WriteCompensationToMachine(self):
        #TODO IP input overwrite

            #Read contents from txt file and then write them modified


        #ReadTxt
        f = open(self.IP_Overwrite_File2,"r+")
        contents = f.read()
        #Define osset to correct
        re.search()

        #Write Compensation TxT
        f.write(contents)
        f.close()
        test=1+1
        
