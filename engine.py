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
                    if "CHN" in code or ".CN" in code or "_CN" in code or code.endswith("CN"): return "CHN"
                    if "NGA" in code or ".NG" in code or "_NG" in code or code.endswith("NG"): return "NGA"
                    if "GHA" in code or ".GH" in code or "_GH" in code or code.endswith("GH"): return "GHA"
                    return None
                
                dbnomics['country_iso'] = dbnomics['series_code'].apply(extract_iso)
                dbnomics = dbnomics.dropna(subset=['country_iso'])
                dbnomics['year'] = dbnomics['year'].astype(int)
                
                uncom_pivoted = uncom.pivot_table(
                        index=['year', 'country_iso'],
                        columns='cmdcode',
                        values=['primaryvalue', 'qty'],
                        aggfunc='sum'
                    )
                
                uncom_pivoted.columns = [f"{col[0]}_{col[1]}" for col in uncom_pivoted.columns]
                uncom_pivoted = uncom_pivoted.reset_index()
                
                # Collapse the trilateral countries into a shared global year baseline via sum aggregation
                energy_cols = [c for c in uncom_pivoted.columns if c not in ['year', 'country_iso']]
                uncom_annual = uncom_pivoted.groupby('year')[energy_cols].sum().reset_index()
                
                # Pivot DBNomics data to break down metrics by specific country names
                db_pivoted = dbnomics.pivot_table(
                    index=['year'],
                    columns=['type', 'country_iso'],
                    values='value',
                    aggfunc='mean'
                )
                
                # Format headers to match your specified layout: e.g., exchange_rate(GHA)
                db_pivoted.columns = [f"{col[0]}({col[1]})" for col in db_pivoted.columns]
                db_pivoted = db_pivoted.reset_index()

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
            
            rename_dict = {
                'primaryvalue_271600': 'Primary Value (Electricity)',
                'primaryvalue_854143': 'Primary Value (Solar)',
                'qty_271600': 'Quantity (Electricity)',
                'qty_854143': 'Quantity (Solar)'
            }
            
            df = df.rename(columns=rename_dict)
            
            stats_summary = df.describe()
            stats_summary.loc['var'] = df.var(numeric_only=True)
            stats_summary.loc['skew'] = df.skew(numeric_only=True)
            print(stats_summary)
            
            uncom_cols = [c for c in df.columns if 'Electricity' in c or 'Solar' in c]
            if uncom_cols:
                print("\n=== UNCOM ENERGY TRADE CORRELATION MATRIX ===")
                self.uncom_corr = df[uncom_cols].corr(numeric_only=True)
                print(self.uncom_corr)

            dbn_cols = [c for c in df.columns if 'exchange_rate' in c or 'inflation' in c]
            if dbn_cols:
                print("\n=== DBNOMICS MONETARY CORRELATION MATRIX ===")
                self.dbnomics_corr = df[dbn_cols].corr(numeric_only=True)
                print(self.dbnomics_corr)
            
            self.corr = df.corr(numeric_only=True)
            return stats_summary, self.corr
        else:
            print("No data present inside the engine to analyse.")
            return None
        
        
    def speartests(self):
        spearman_gha = float(self.df['exchange_rate'].corr(self.df['inflation'], method='spearman')) # testing
        """ spearman_nga = float(self.df['x'].corr(self.df['y'], method='spearman'))
        spearman_chn = float(self.df['x'].corr(self.df['y'], method='spearman')) # spearman for trilateral relationship """
        
        return {
            "Spearman (GHA)": round(spearman_gha, 4) }
        

    def run_game_theory(self):
        pass