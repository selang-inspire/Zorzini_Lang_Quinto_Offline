class Machine:
        
    def __init__(mc, Name, mode):
        #Import Machine specific package depending on which machine is used
        if Name == "EVO_Quinto":
            import EVO_Quinto as load_DataMachine
        elif Name == "EVO100":            
            import EVO_Quinto as load_DataMachine
        else:
            raise SystemExit('Error: Unknown Machine Specific Library currently implemented "EVO_Quinto", "EVO100" or .')

        if mode == "Sim":
            mc.MachineName  = Name
            mc.Mode         = mode
            mc.ThermalError = ()
            mc.Temperature  = ()
            mc.LoadDataOffline()
            
        elif mode == "Compensation" or mode == "Log":
            mc.MachineName  = Name
            mc.Mode         = mode
            mc.ThermalError = ()
            mc.Temperature  = ()
            mc.LoadDataOnline()
        else:
            raise SystemExit('Error: Unknown Machine Mode, currently implemented "Sim", "Compensation" or "Log".')

    
    def LoadDataOffline(mc):
        ThermalError, Temperature = load_DataMachine.OfflineFileData(machineSpec)
        mc.ThermalError = ThermalError
        mc.Temperature  = Temperature
            
    def LoadDataOnline(mc):
       #OnlineCompT = load_DataMachine.OnlineTempData(machineSpec) #creating threads
       #OnlineCompT.start()  #starting threads
        OnlineMachineData = load_DataMachine.OnlineMachineData()
        OnlineMachineData.start()
        #OnlineCompT.join()
        OnlineMachineData.join()                #wait for the all thread to be over in order to continue witht the code
        
        #mc.ThermalError = OnlineMachineData.Data #TODO Calculate error function
        #mc.Temperature  = OnlineCompT.Data

