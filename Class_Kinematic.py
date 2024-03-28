# Error calculation object
import numpy as np

class errorMeasurement:
    """"
    Which error measurement cycle is currently used and how to calculate the error
    """

    def __init__(self, CycleType):
        self.CycleType = "CycleType"
        self.kinematicReference = 0 #TODO Initialize so its the total first value

    def error_calculation(self):
        1+1