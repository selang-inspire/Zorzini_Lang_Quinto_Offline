class MT:
        
    def __init__(self, Name, mode,measurementFrequency):
        #Import Machine specific package depending on which machine is used
        if Name == "EVO_Quinto":
            from Class_EVO_Quinto import EVO_Quinto
            self.Machine = EVO_Quinto()

        elif Name == "EVO_100":
            from Class_EVO_100 import EVO_100
            self.Machine = EVO_100()
        else:
            raise SystemExit('Error: Unknown Machine Specific Library currently implemented "EVO_Quinto", "EVO100" or .')

        self.MachineName  = Name
        self.Mode         = mode

        if mode == "Sim":
            self.ThermalError = ()
            self.Temperature  = ()
            self.LoadDataOffline()
            
        elif mode == "Compensation" or mode == "Log":
            self.ThermalError = ()
            self.Temperature  = ()
            self.Machine.ConnectMachine(measurementFrequency)
            self.Machine.OPC.start()
        else:
            raise SystemExit('Error: Unknown Machine Mode, currently implemented "Sim", "Compensation" or "Log".')

    
    def LoadDataOffline(self):
        ThermalError, Temperature = load_DataMachine.OfflineFileData(machineSpec)
        self.ThermalError = ThermalError
        self.Temperature  = Temperature
            



