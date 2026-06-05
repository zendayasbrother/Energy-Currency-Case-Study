import pandas as pd
import numpy as np
from scipy import stats
import nashpy as nash
import json
from sklearn.linear_model import LinearRegression 
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')

# DataEngine is a composition class for orchestrating the math and game theory analysis 
class DataEngine():
    def __init__(self, cleaner_ins):
        if cleaner_ins is None or cleaner_ins.df is None:
            raise ValueError("DataEngine requires a cleaner instance with populated data.")
        self.cleaner = cleaner_ins
        self.df = self.cleaner.df 
        
    def run_analysis(self):
        print("Running full analysis:")
        print(self.df.describe())
        pass  # Placeholder for my EDA  logic
        return self.df.describe()

    def run_game_theory(self):
        # Placeholder for my nashpy logic
        pass 

        
