import pandas as pd
import numpy as np
from scipy import stats
import nashpy as nash
from datacleanse import DataCleaner, Fetcher
import json
from sklearn.linear_model import LinearRegression 
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')

# DataEngine is a composition class for orchestrating the math and game theory analysis 
class DataEngine:
    def __init__(self, cleaner, fetch, countries, db_path):
        self.cleaner = cleaner
        self.fetch = fetch
        
        try:
            uncom = self.cleaner.fetch_api(countries) # what does the engine need? data for maths
            dbnomics = self.fetch.fetch_all()
            
            self.df = pd.concat([uncom, dbnomics], ignore_index=True)
        except Exception as e:
            print(f"UNCOM or DBnomics Pipeline failed: {e}") # might move to engine.py
        

    def run_analysis(self, cleaner, df):
        df = self.df
        print("\nRunning full analysis:")
        if self.df is not None and not df.empty:
            cleaner.clean_data(df)
            stats = df.describe()
            stats.loc['median'] = df.median(numeric_only=True)
            stats.loc['var'] = df.var(numeric_only=True)
            stats.loc['skew'] = df.skew(numeric_only=True)
            stats.loc['25% quartiles'] = df.quantile(0.25, numeric_only=True)
            stats.loc['75% quartiles'] = df.quantile(0.75, numeric_only=True)
            self.corr = df.corr(numeric_only=True)
            return stats, self.corr # (add more stats for inspection here)
        else:
            print("No data present inside the engine to analyze.")
            return None
        
        # might put the spearman and other mathematical tests under here via an instance then a seperate function
        
        
    def spear_tests(self):
        pass
        

    def run_game_theory(self):
        pass