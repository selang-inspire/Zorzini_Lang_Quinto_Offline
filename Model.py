import pandas as pd
from threading import Thread, Event
import csv
import numpy as np
from datetime import datetime

#Model definition and use
class Model:
    def __init__(self):
        self.ModelType = [] #Different Model architectures


    def Generate(self):
        if self.ModelType == "ARDL":

        elif self.ModelType == "FFNN":

        elif self.ModelType == "LSTM":
