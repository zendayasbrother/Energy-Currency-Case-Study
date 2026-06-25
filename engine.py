import pandas as pd
import numpy as np
import json
import warnings
warnings.filterwarnings('ignore')


# DataEngine is a composition class for orchestrating the math
class DataEngine:
    def __init__(self, cleaner, fetcher):
        self.cleaner = cleaner
        self.fetcher = fetcher
        self.df = pd.DataFrame()
        
        self.metadata_cols = [
            'refperiodid', 'refmonth', 'partnercode', 'partner2code', 
            'motcode', 'qtyunitcode', 'altqtyunitcode', 'legacyestimationflag',
            'year', 'refyear', 'reportercode', 'period', 'date', 
            'isqtyestimated', 'isaltqtyestimated', 'isnetwgtestimated', 
            'isgrosswgtestimated', 'isreported', 'isaggregate'
        ]
    
        
    def sync_matrix(self, countries):
        try:
            uncom = self.cleaner.fetch_api(countries)
            dbnomics = self.fetcher.fetch_all()
        
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
            
            merged_df = pd.merge(uncom_df, db_pivot, on=['year', 'iso'], how='inner')
            
            if merged_df.empty:
                raise RuntimeError("Data integrity failure: Inner join yielded 0 rows.")

            self.df = merged_df
            print(f"-> Matrix synchronized successfully! Matrix shape: {self.df.shape}")
        except Exception as e:
            raise RuntimeError(f"Data synchronization failed: {e}")
       
    def meta_clean(self): 
        if self.df is None or self.df.empty:
            return pd.DataFrame()
        df_cleaned = self.df.drop(columns=self.metadata_cols, errors='ignore')
        df_cleaned = df_cleaned.dropna(axis=1, how='all')
        df_cleaned = df_cleaned.loc[:, (df_cleaned != 0).any(axis=0)]
        
        self.df = df_cleaned
        return self.df # (move to dc.py)

    def run_stats(self):
        print("\nRunning full analysis:")
        if self.df.empty:
            print("Error: No matrix data present inside the engine to analyse.")
            return None
        
        print("\n--- MERGED DATA ft. First 15 rows ---")
        print(f"Dimensions: {self.df.shape}")
        print(self.df.head(15))
        
        self.meta_clean()
        
        df = self.df.copy()
        metadata = ['typecode', 'freqcode', 'iso']        
        df = df.drop(columns=metadata, errors='ignore')
        df = df.select_dtypes(include=[np.number])
        
        # add independent HFCE (USD) dataset for engergy-equity calculation
        print("\n--- Data Types ---")
        print(self.df.dtypes)
        print(self.df.info())
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
            print(df[energy_cols].apply(pd.to_numeric, errors='coerce').corr())

        if target_cols and energy_cols:
            print("\n=== DBN MACROECONOMIC CORRELATION ===")
            combined_cols = list(set(energy_cols + target_cols))
            
            corr_df = df[combined_cols].apply(pd.to_numeric, errors='coerce')
            corr_matrix = corr_df.corr()
            print(corr_matrix)
            results = self.speartests()
            for key, value in results.items():
                print(f"\n{key}: {value}")
            return corr_matrix
        return None
       
    def speartests(self):
        countries = {'GHA': 'GHA', 'NGA': 'NGA', 'CHN': 'CHN'}
        results = {}
        
        for label, iso in countries.items():
            subset = self.df[self.df['iso'] == iso]
            val = subset['primaryvalue'].corr(subset['exchange_rate'], method='spearman')
            results[f'Spearman - Primary Value vs Inflation ({label})'] = round(float(val), 4)
        
        return results # END OF FIRST HALF 

 # calculations    
    def gapcalcs(): 
        pass