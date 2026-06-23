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
    def __init__(self, cleaner, fetch):
        self.cleaner = cleaner
        self.fetch = fetch
        self.df = pd.DataFrame()
        
        self.metadata_cols = [
            'refperiodid', 'refmonth', 'partnercode', 'partner2code', 
            'motcode', 'qtyunitcode', 'altqtyunitcode', 'legacyestimationflag',
            'year', 'reportercode', 'isqtyestimated', 'isaltqtyestimated',
            'isnetwgtestimated', 'isgrosswgtestimated', 'isreported', 'isaggregate'
        ]
    
        
    def sync_matrix(self, countries):
        try:
            uncom = self.cleaner.fetch_api(countries)
            dbnomics = self.fetch.fetch_all()
        
            if uncom is None or uncom.empty or dbnomics is None or dbnomics.empty:
                raise ValueError("Upstream extraction returned empty datasets.")

            uncom_df = uncom.copy()
            uncom_df['year'] = uncom_df['refyear'].astype(int)
            
            dbnomics_df = dbnomics.copy()
            dbnomics_df['year'] = dbnomics_df['year'].astype(int)

            db_pivot = dbnomics_df.pivot_table(
                index=['year', 'iso'], 
                columns='type', 
                values='value', 
                aggfunc='first'
            ).reset_index()

            country_iso_map = {288: "GHA", 566: "NGA", 156: "CHN"}
            uncom_df['iso'] = uncom_df['reportercode'].map(country_iso_map)

            merged_df = pd.merge(uncom_df, db_pivot, on=['year', 'iso'], how='inner')
            
            if merged_df.empty:
                raise RuntimeError("Data integrity failure: Inner join yielded 0 rows.")

            self.df = merged_df
            print(f"-> Matrix synchronized successfully! Matrix shape: {self.df.shape}")
        except Exception as e:
            print(f"UNCOM or DBnomics Pipeline failed: {e}")
       
    def meta_clean(self): 
        if self.df is None or self.df.empty:
            return pd.DataFrame()
        df_numeric = self.df.select_dtypes(include=[np.number])
        period_cols = [col for col in df_numeric.columns if col not in self.metadata_cols]
        df = df_numeric[period_cols]
        return df

    def run_stats(self, df):
        print("\nRunning full analysis:")
        self.df = self.meta_clean()
        if self.df.empty:
            print("Error: No matrix data present inside the engine to analyse.")
            return None
        
        
        stats_summary = df.describe()
        stats_summary.loc['var'] = df.var(numeric_only=True)
        stats_summary.loc['skew'] = df.skew(numeric_only=True)
        print(stats_summary)
        return stats_summary    
           
    def run_corr(self):
        df = self.meta_clean()
        if df.empty:
            return None
       
        energy_cols = [c for c in df.columns if any(x in c for x in ['primaryvalue', 'qty', 'fobvalue', 'cifvalue'])]
        macro_cols = ['inflation', 'exchange_rate']
        target_cols = [col for col in macro_cols if col in df.columns]
        
        if energy_cols:
            print("\n=== UNCOM TRADE CORRELATION ===")
            print(df[energy_cols].corr())

        if target_cols and energy_cols:
            print("\n=== DBN MACROECONOMIC CORRELATION ===")
            combined_cols = list(set(energy_cols + target_cols))
            corr_matrix = df[combined_cols].corr()
            print(corr_matrix)
            self.speartests(df)
            return corr_matrix
        return None
       
    def speartests(self):
        spearman_gha = float(self.df['primaryvalue'].corr(self.df['value'], method='spearman'))
        """spearman_nga = float(self.df['x'].corr(self.df['y'], method='spearman'))
        spearman_chn = float(self.df['x'].corr(self.df['y'], method='spearman'))"""

        return {
            "Spearman (GHA)": round(spearman_gha, 4)} 
    def run_game_theory(self):
        pass
