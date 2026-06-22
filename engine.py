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
            
            if uncom is not None and not uncom.empty and dbnomics is not None and not dbnomics.empty:
                print("\nSynchronizing timelines and merging datasets horizontally...")
                
                uncom_iso_map = {156: "CHN", 566: "NGA", 288: "GHA"}
                uncom['country_iso'] = uncom['reportercode'].map(uncom_iso_map)
                uncom['year'] = uncom['refyear'].astype(int)
                # Explicit mapping for energy codes
                uncom['energy_type'] = uncom['cmdcode'].replace({
                    '271600': 'electricity',
                    '854143': 'solar'
                })
                
                def extract_iso(series_code):
                    code = str(series_code).upper()
                    if "CHN" in code or code.endswith("CN"): return "CHN"
                    if "NGA" in code or code.endswith("NG"): return "NGA"
                    if "GHA" in code or code.endswith("GH"): return "GHA"
                    return None
                
                dbnomics['country_iso'] = dbnomics['series_code'].apply(extract_iso)
                dbnomics['year'] = dbnomics['year'].astype(int)
                
                db_pivoted = dbnomics.pivot_table(
                    index=['year'],
                    columns='type',
                    values='value',
                    aggfunc='mean'
                ).reset_index()
                
                uncom_annual = uncom.groupby(['year'], as_index=False).agg(
                primaryvalue=('primaryvalue', 'sum'),
                qty=('qty', 'sum')
                )

                self.df = pd.merge(uncom_annual, db_pivoted, on=['year'], how='inner')
                print(f"-> Matrix synchronized successfully! Matrix shape: {self.df.shape}")
            else:
                self.df = pd.concat([uncom, dbnomics], ignore_index=True)
        except Exception as e:
            print(f"UNCOM or DBnomics Pipeline failed: {e}") 
        

    def run_analysis(self):
        print("\nRunning full analysis:")
        if self.df is not None and not self.df.empty:
            period_cols = [col for col in self.df.columns if col not in ['year', 'country_iso']]
            df = self.df[period_cols]
            
            stats_summary = df.describe()
            stats_summary.loc['var'] = df.var(numeric_only=True)
            stats_summary.loc['skew'] = df.skew(numeric_only=True)
            
            self.corr = df.corr(numeric_only=True)
            print(stats_summary)
            print(self.corr)
            return stats_summary, self.corr
        else:
            print("No data present inside the engine to analyze.")
            return None
        
        # might put the spearman and other mathematical tests under here via an instance then a seperate function
        
        
    def speartests(self):
        spearman_gha = float(self.df['x'].corr(self.df['y'], method='spearman'))
        spearman_nga = float(self.df['x'].corr(self.df['y'], method='spearman'))
        spearman_chn = float(self.df['x'].corr(self.df['y'], method='spearman')) # spearman for trilateral relationship
        
        
        

    def run_game_theory(self):
        pass