from engine import DataEngine
import pandas as pd
import numpy as np
import json
from sklearn.linear_model import LinearRegression 
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')

# Plots different mathematical demos, and visualises complex relationships 

class ECModel(DataEngine):
    def __init__(self, cleaner_ins):
        super().__init__(cleaner_ins)