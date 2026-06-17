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
    def __init__(self, cleaner, fetch, countries):
        self.cleaner = cleaner 
        self.fetch = fetch
        self.df = pd.DataFrame()
        
        try:
            uncom = self.cleaner.fetch_api(countries) # what does the engine need? data for maths
            dbnomics = self.fetch.fetch_all()
            
            self.df = pd.concat([uncom, dbnomics], ignore_index=True)
        except Exception as e:
            print(f"UNCOM or DBnomics Pipeline failed: {e}") # might change to if condition
        

    def run_analysis(self):
        print("\nRunning full analysis:")
        if self.df is not None and not self.df.empty:
            metadata_cols = [
                'refperiodid', 'refyear', 'refmonth', 'period', 'date',
                'reportercode', 'partnercode', 'partner2code', 
                'motcode', 'qtyunitcode', 'altqtyunitcode', 'legacyestimationflag'
            ]
            df = self.df.drop(columns=metadata_cols, errors='ignore')
            
            stats_summary = df.describe()
            stats_summary.loc['median'] = df.median(numeric_only=True)
            stats_summary.loc['var'] = df.var(numeric_only=True)
            stats_summary.loc['skew'] = df.skew(numeric_only=True)
            stats_summary.loc['25% quartiles'] = df.quantile(0.25, numeric_only=True)
            stats_summary.loc['75% quartiles'] = df.quantile(0.75, numeric_only=True)
            
            self.corr = df.corr(numeric_only=True)
            
            print(stats_summary)
            return stats_summary, self.corr 
        else:
            print("No data present inside the engine to analyze.")
            return None
        
        # might put the spearman and other mathematical tests under here via an instance then a seperate function
        
        
    def spear_tests(self):
        pass
        

    def run_game_theory(self):
        pass