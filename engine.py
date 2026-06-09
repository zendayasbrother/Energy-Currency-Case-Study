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
class DataEngine():
    def __init__(self, cleaner, fetch):
        cleaner = DataCleaner()
        fetch = Fetcher()
        uncom = cleaner.fetch_api # what does the engine need? data for maths
        dbnomics = fetch.fetch_all()
        self.df = pd.concat([uncom, dbnomics], ignore_index=True)

    def run_analysis(self, cleaner, df):
        df = self.df
        print("\nRunning full analysis:")
        if self.df is not None and not df.empty:
            cleaner.clean_data(df)
            stats = df.describe()
            stats.loc['median'] = df.median(numeric_only=True)
            stats.loc['var'] = df.var(numeric_only=True)
            stats.loc['skew'] = df.skew(numeric_only=True)
            self.corr = df.corr(numeric_only=True)
            return stats, self.corr 
        else:
            print("No data present inside the engine to analyze.")
            return None
        
        # might put the spearman and other mathematical tests under here

    def run_game_theory(self):
        pass