'''
Author: Mario Zorzini (mzorzini)
Online communication (Feedback to MT)
'''

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
from pytz import timezone
import copy
import subprocess
import os



class AGATHON_Com:
    '''
    This class is used to communicate with the machine tool
    - It should be used tu feedback the predicted thermal error
    '''
    def __init__(self, IP_Log_File, IP_Overwrite_File):
        self.IP_Log_File = "C:\\Users\\mzorzini\\Documents\\IPJSon\\IpInputLog4R.tmp" #IP_Log_File
        self.IP_Overwrite_File = "C:\\Users\\mzorzini\\Documents\\IPJSon\\IpInputDat.txt" #IP_Overwrite_File
        self.copy_and_rename_file(self.IP_Log_File)
        self.Prediction = pd.DataFrame(columns=["Time", "X Offset LR", "Y Offset LR", "Z Offset LR", "Anvil LR", "Pivot C2B LR", "X Offset RR", "Y Offset RR", "Z Offset RR", "Anvil RR", "Pivot C2B RR"])
        self.IP_Comp_Values = pd.DataFrame(columns=["Time", "X Offset LR", "Y Offset LR", "Z Offset LR", "Anvil LR", "Pivot C2B LR", "X Offset RR", "Y Offset RR", "Z Offset RR", "Anvil RR", "Pivot C2B RR"])

    def copy_and_rename_file(self, source_file):
        '''
        - Copy the IP_Log_File file and rename it as Initial_IP_Log_File
        - The Initial_IP_Log_File should be used as a reference
        '''
        # Define the destination file
        destination_file = source_file.replace("IpInputLog4R.tmp", "initial_IpInputLog4R.tmp")
        if not os.path.exists(destination_file):
            # Open the source file and read its content
            with open(source_file, 'rb') as src_file:
                content = src_file.read()
            # Open the destination file in write mode and write the content
            with open(destination_file, 'wb') as dest_file:
                dest_file.write(content)
            print("File IpInputLog4R.tmp copied and renamed successfully")

    def Read_State_Interpreter(self):
        # Read previous status from IP
        source_file = self.IP_Log_File
        source = source_file.replace("IpInputLog4R.tmp", "initial_IpInputLog4R.tmp")
        logf = open(source, "r")
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
                    Xnr = len(name_value_pairs) - 1
                if name == "\nXOffsCorr4RR":
                    Xnr_RR = len(name_value_pairs) - 1

        locnr = len(self.IP_Comp_Values)
        self.IP_Comp_Values.loc[locnr, "Time"] = datetime.now()
        self.IP_Comp_Values.loc[locnr, "X Offset LR"] = float(name_value_pairs[Xnr][1])
        self.IP_Comp_Values.loc[locnr, "Y Offset LR"] = float(name_value_pairs[Xnr + 1][1])
        self.IP_Comp_Values.loc[locnr, "Z Offset LR"] = float(name_value_pairs[Xnr + 2][1])
        self.IP_Comp_Values.loc[locnr, "Anvil LR"] = float(name_value_pairs[Xnr + 3][1])
        self.IP_Comp_Values.loc[locnr, "Pivot C2B LR"] = float(name_value_pairs[Xnr + 6][1])
        self.IP_Comp_Values.loc[locnr, "X Offset RR"] = float(name_value_pairs[Xnr_RR][1])
        self.IP_Comp_Values.loc[locnr, "Y Offset RR"] = float(name_value_pairs[Xnr_RR + 1][1])
        self.IP_Comp_Values.loc[locnr, "Z Offset RR"] = float(name_value_pairs[Xnr_RR + 2][1])
        self.IP_Comp_Values.loc[locnr, "Anvil RR"] = float(name_value_pairs[Xnr_RR + 3][1])
        self.IP_Comp_Values.loc[locnr, "Pivot C2B RR"] = float(name_value_pairs[Xnr_RR + 6][1])

        # TODO Incorporate anvil pivot values that make sens

    def insert_predictions(self, predictions_dict, step):
        # Insert the predictions into the Prediction Dataframe
        dict = copy.deepcopy(predictions_dict)
        for keys in dict:
            value_in_mu = dict[keys]['Wert_4'][step]
            dict[keys].loc[step, 'Wert_4'] = value_in_mu / 1000#calucale from um in mm
        if self.Prediction.empty:
            self.Prediction = pd.DataFrame(columns=["Time", "X Offset LR", "Y Offset LR", "Z Offset LR", "Anvil LR", "Pivot C2B LR", "X Offset RR", "Y Offset RR", "Z Offset RR", "Anvil RR", "Pivot C2B RR"])
        self.Prediction.loc[0, "Time"] = datetime.now()
        self.Prediction.loc[0, "X Offset LR"] = dict['X0B']['Wert_4'][step] #umrechnen von um in mm?
        self.Prediction.loc[0, "Y Offset LR"] = dict['Y0B']['Wert_4'][step]
        self.Prediction.loc[0, "Z Offset LR"] = dict['Z0B']['Wert_4'][step]
        self.Prediction.loc[0, "Anvil LR"] = dict['X0C']['Wert_4'][step]
        self.Prediction.loc[0, "Pivot C2B LR"] = dict['Y0C']['Wert_4'][step]
        self.Prediction.loc[0, "X Offset RR"] = dict['X0B']['Wert_4'][step]
        self.Prediction.loc[0, "Y Offset RR"] = dict['Y0B']['Wert_4'][step]
        self.Prediction.loc[0, "Z Offset RR"] = dict['Z0B']['Wert_4'][step]
        self.Prediction.loc[0, "Anvil RR"] = dict['X0C']['Wert_4'][step]
        self.Prediction.loc[0, "Pivot C2B RR"] = dict['Y0C']['Wert_4'][step]
        print("\033[92mOverwriting Interpreter:")
        # insert step as Index in self.Prediction for printing
        predi = self.Prediction.copy()
        predi.index = predi.index + step
        print("\033[92m" + str(predi))  # for debugging
        print("\033[0m")  # reset the color to default
        print("=" * 100)
        # start overwriting
        self.Compensation_To_Machine() #comment out for ONLINE compensation on MT

    def Write_Interpreter_Overwrite(self):
        f = open(self.IP_Overwrite_File, "r+")
        contents = f.read()  # Read all content, currently not used, contents new writes independent of old
        # Delete all content
        f.truncate(0)
        # Define ofsset to correct
        locnr = len(self.Prediction) - 1
        X_LR = "\nXOffsCorr4LR = " + str(
            self.Prediction.loc[locnr, "X Offset LR"] + self.IP_Comp_Values.loc[0, "X Offset LR"]) + " ;" + "\n"
        X_RR = "XOffsCorr4RR = " + str(
            self.Prediction.loc[locnr, "X Offset RR"] + self.IP_Comp_Values.loc[0, "X Offset RR"]) + " ;" + "\n"
        Y_LR = "YOffsCorr4LR = " + str(
            self.Prediction.loc[locnr, "Y Offset LR"] + self.IP_Comp_Values.loc[0, "Y Offset LR"]) + " ;" + "\n"
        Y_RR = "YOffsCorr4RR = " + str(
            self.Prediction.loc[locnr, "Y Offset RR"] + self.IP_Comp_Values.loc[0, "Y Offset RR"]) + " ;" + "\n"
        Z_LR = "ZOffsCorr4LR = " + str(
            self.Prediction.loc[locnr, "Z Offset LR"] + self.IP_Comp_Values.loc[0, "Z Offset LR"]) + " ;" + "\n"
        Z_RR = "ZOffsCorr4RR = " + str(
            self.Prediction.loc[locnr, "Z Offset RR"] + self.IP_Comp_Values.loc[0, "Z Offset RR"]) + " ;" + "\n"
        Anvil_LR = "AnvilCorr4LR = " + str(
            self.Prediction.loc[locnr, "Anvil LR"] + self.IP_Comp_Values.loc[0, "Anvil LR"]) + " ;" + "\n"
        Anvil_RR = "AnvilCorr4RR = " + str(
            self.Prediction.loc[locnr, "Anvil RR"] + self.IP_Comp_Values.loc[0, "Anvil RR"]) + " ;" + "\n"
        Pivot_LR = "PivotC2B_4LR = " + str(
            self.Prediction.loc[locnr, "Pivot C2B LR"] + self.IP_Comp_Values.loc[0, "Pivot C2B LR"]) + " ;" + "\n"
        Pivot_RR = "PivotC2B_4RR = " + str(
            self.Prediction.loc[locnr, "Pivot C2B RR"] + self.IP_Comp_Values.loc[0, "Pivot C2B RR"]) + " ;" + "\n"
        contents_new = X_LR + Y_LR + Z_LR + X_RR + Y_RR + Z_RR + Anvil_LR + Anvil_RR + Pivot_LR + Pivot_RR
        # Write Compensation TxT
        f.write(contents_new)
        f.close()

    def Write_Interpreter_Overwrite_Test(self):
        # Read all lines from the file
        with open(self.IP_Overwrite_File, "r") as f:
            lines = f.readlines()

        # Define offset to correct
        locnr = len(self.Prediction) - 1

        # Define the new line contents
        new_line_contents = {
            "XOffsCorr4LR": "\nXOffsCorr4LR = " + str(
                self.Prediction.loc[locnr, "X Offset LR"] + self.IP_Comp_Values.loc[0, "X Offset LR"]) + " ;" + "\n",
            "XOffsCorr4RR": "XOffsCorr4RR = " + str(
                self.Prediction.loc[locnr, "X Offset RR"] + self.IP_Comp_Values.loc[0, "X Offset RR"]) + " ;" + "\n",
            "YOffsCorr4LR": "YOffsCorr4LR = " + str(
                self.Prediction.loc[locnr, "Y Offset LR"] + self.IP_Comp_Values.loc[0, "Y Offset LR"]) + " ;" + "\n",
            "YOffsCorr4RR": "YOffsCorr4RR = " + str(
                self.Prediction.loc[locnr, "Y Offset RR"] + self.IP_Comp_Values.loc[0, "Y Offset RR"]) + " ;" + "\n",
            "ZOffsCorr4LR": "ZOffsCorr4LR = " + str(
                self.Prediction.loc[locnr, "Z Offset LR"] + self.IP_Comp_Values.loc[0, "Z Offset LR"]) + " ;" + "\n",
            "ZOffsCorr4RR": "ZOffsCorr4RR = " + str(
                self.Prediction.loc[locnr, "Z Offset RR"] + self.IP_Comp_Values.loc[0, "Z Offset RR"]) + " ;" + "\n",
            "AnvilCorr4LR": "AnvilCorr4LR = " + str(
                self.Prediction.loc[locnr, "Anvil LR"] + self.IP_Comp_Values.loc[0, "Anvil LR"]) + " ;" + "\n",
            "AnvilCorr4RR": "AnvilCorr4RR = " + str(
                self.Prediction.loc[locnr, "Anvil RR"] + self.IP_Comp_Values.loc[0, "Anvil RR"]) + " ;" + "\n",
            "PivotC2B_4LR": "PivotC2B_4LR = " + str(
                self.Prediction.loc[locnr, "Pivot C2B LR"] + self.IP_Comp_Values.loc[0, "Pivot C2B LR"]) + " ;" + "\n",
            "PivotC2B_4RR": "PivotC2B_4RR = " + str(
                self.Prediction.loc[locnr, "Pivot C2B RR"] + self.IP_Comp_Values.loc[0, "Pivot C2B RR"]) + " ;" + "\n"
        }

        # Find the lines to overwrite and replace them with the new content
        for i, line in enumerate(lines):
            stripped_line = line.lstrip()  # Strip leading whitespace
            for key, new_line_content in new_line_contents.items():
                if stripped_line.startswith(key):
                    lines[i] = new_line_content

                    # Write all lines back to the file
        with open(self.IP_Overwrite_File, "w") as f:
            f.writelines(lines)

    def runJSON(self):
        '''
        Only for Testing (NOT USED IN PRODUCTION)
        '''
        exe_path = r"C:\Users\mzorzini\Documents\IPJSon\IPJSon.exe"
        exe_dir = os.path.dirname(exe_path)
        subprocess.run(exe_path, check=True, cwd=exe_dir)
        print("JSON Executed")

    def Compensation_To_Machine(self):
        # TODO IP input overwrite

        # Read Current Interpreter values and safe them and the time in IP_Comp_Values
        self.Read_State_Interpreter()
        # ReadTxt from overwrite file, which is subsequently modified
        self.Write_Interpreter_Overwrite_Test()
        #self.Write_Interpreter_Overwrite()
        self.runJSON() #onyl for Testing
