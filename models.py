from engine import DataEngine
import pandas as pd
import numpy as np
import json
from scipy import stats
import nashpy as nash
from sklearn.linear_model import LinearRegression 
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')

# Plots different mathematical demos, and visualises complex relationships (game theory)

class ECModels(DataEngine):
    def __init__(self, cleaner_ins):
        super().__init__(cleaner_ins)
        
        
    def run_game_theory(self):
        pass # Stacklberg model 
