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
        self.df = pd.DataFrame()
       
        try:
            uncom = self.cleaner.fetch_api(countries) # what does the engine need? data for maths
            dbnomics = self.fetch.fetch_all()
           
            self.df = pd.merge(uncom, dbnomics, on=['year'], how='inner')
            print(f"-> Matrix synchronized successfully! Matrix shape: {self.df.shape}")
        except Exception as e:
            print(f"UNCOM or DBnomics Pipeline failed: {e}")
       


    def run_stats(self):
        print("\nRunning full analysis:")
        if self.df is None or self.df.empty:
            print("Error: No matrix data present inside the engine to analyse.")
            return None
       
        period_cols = [col for col in self.df.columns if col not in ['year', 'country_iso']]
        df = self.df[period_cols]
   
        stats_summary = df.describe()
        stats_summary.loc['var'] = df.var(numeric_only=True)
        stats_summary.loc['skew'] = df.skew(numeric_only=True)
        print(stats_summary)
        return stats_summary
           
    def run_corr(self):
        if self.df is None or self.df.empty:
            return None
       
        energy_cols = [c for c in self.df.columns if any(x in c for x in ['primaryvalue', 'qty'])]
        macro_cols = [c for c in self.df.columns if any(x in c for x in ['exchange_rate', 'inflation'])]
       
        if energy_cols:
            print("\n=== PANEL ENERGY TRADE CORRELATION ===")
            self.uncom_corr = self.df[energy_cols].corr()
            print(self.uncom_corr)


        if macro_cols:
            print("\n=== PANEL MACROECONOMIC CORRELATION ===")
            self.dbnomics_corr = self.df[macro_cols].corr()
            print(self.dbnomics_corr)
           
        self.corr = self.df[energy_cols + macro_cols].corr()
        return self.corr
       
    def speartests(self):
        spearman_gha = float(self.df['x'].corr(self.df['y'], method='spearman'))
        spearman_nga = float(self.df['x'].corr(self.df['y'], method='spearman'))
        spearman_chn = float(self.df['x'].corr(self.df['y'], method='spearman'))


    def run_game_theory(self):
        pass
