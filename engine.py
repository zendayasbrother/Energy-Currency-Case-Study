from datacleanse import DataCleaner
import pandas as pd
import numpy as np
from scipy import stats
import wbgapi as wb
from nashpy import nash
import json
from sklearn.linear_model import LinearRegression 
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')

# DataEngine is a class for orchestrating the math and game theory analysis 

class DataEngine(DataCleaner):
    def __init__(self, data_source):
        super().__init__(data_source)
        
    def run_analysis(self):
        self.cleaned_df = self.clean_data() 
        pass  # Placeholder for your analysis logic

    def run_game_theory(self):
        # Placeholder for your nashpy logic
        pass 
    
    # Future function holding json object