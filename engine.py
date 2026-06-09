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
        self.df = cleaner_ins.df

    def run_analysis(self):
        print("\nRunning full analysis:")
        if self.df is not None and not self.df.empty:
            print(self.df.describe())
            return self.df.describe()
        else:
            print("No data present inside the engine to analyze.")
            return None

    def run_game_theory(self):
        pass