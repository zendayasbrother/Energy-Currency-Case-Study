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
           
            if uncom is not None and not uncom.empty and dbnomics is not None and not dbnomics.empty:
                uncom_iso_map = {156: "CHN", 566: "NGA", 288: "GHA"}
                uncom['country_iso'] = uncom['reportercode'].map(uncom_iso_map)
                uncom['year'] = uncom['refyear'].astype(int)
                
                dbnomics['year'] = dbnomics['year'].astype(int)
                
                self.df = pd.merge(uncom, dbnomics, on=['year'], how='inner')
                print(f"-> Matrix synchronized successfully! Matrix shape: {self.df.shape}")
        except Exception as e:
            print(f"UNCOM or DBnomics Pipeline failed: {e}")
       


    def run_stats(self):
        print("\nRunning full analysis:")
        if self.df is None or self.df.empty:
            print("Error: No matrix data present inside the engine to analyse.")
            return None
        
        df_numeric = self.df.select_dtypes(include=[np.number])
        
        metadata_cols = [
            'refperiodid', 'refmonth', 'partnercode', 'partner2code', 
            'motcode', 'qtyunitcode', 'altqtyunitcode', 'legacyestimationflag',
            'year', 'reportercode'
        ]
        self.df = self.df.drop(columns=metadata_cols, errors='ignore') 
        
        period_cols = [col for col in df_numeric.columns if col not in metadata_cols]
        df = df_numeric[period_cols]
        
        stats_summary = df.describe()
        stats_summary.loc['var'] = df.var(numeric_only=True)
        stats_summary.loc['skew'] = df.skew(numeric_only=True)
        print(stats_summary)
        return stats_summary
           
    def run_corr(self):
        if self.df is None or self.df.empty:
            return None
       
        energy_cols = [c for c in self.df.columns if any(x in c for x in ['primaryvalue', 'qty', 'fobvalue', 'cifvalue'])]
        
        # Macro indicators are mixed inside the 'value' column alongside 'type'
        # To compute matrix correlations cleanly, we select the generic 'value' column
        macro_cols = ['value'] if 'value' in self.df.columns else []
        
        if energy_cols:
            print("\n=== PANEL ENERGY TRADE CORRELATION ===")
            self.uncom_corr = self.df[energy_cols].corr()
            print(self.uncom_corr)

        if macro_cols and energy_cols:
            print("\n=== PANEL MACROECONOMIC CORRELATION (Value Column) ===")
            # Safely combines available analytical arrays
            df_cols = list(set(energy_cols + macro_cols))
            self.corr = self.df[df_cols].corr()
            print(self.corr)
            return self.corr
        
        return None
       
    def speartests(self):
        spearman_gha = float(self.df['primaryvalue'].corr(self.df['inflation'], method='spearman'))
        """spearman_nga = float(self.df['x'].corr(self.df['y'], method='spearman'))
        spearman_chn = float(self.df['x'].corr(self.df['y'], method='spearman'))"""


    def run_game_theory(self):
        pass
