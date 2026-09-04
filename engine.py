import pandas as pd
import numpy as np
from datacleanse import DataCleaner, Fetcher
import scipy.stats as stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from gplearn.genetic import SymbolicRegressor
import sympy as sp
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
            
            self.cleaner.connect_database()
            self.fetcher.connect_database()
        
            if uncom is None or uncom.empty or dbnomics is None or dbnomics.empty:
                raise ValueError("Upstream extraction returned empty datasets.")

            uncom_df = uncom.copy()
            uncom_df['year'] = uncom_df['refyear'].astype(int)
            
            dbnomics_df = dbnomics.copy()
            dbnomics_df['year'] = dbnomics_df['year'].astype(int)
            
            # In engine.py inside sync_matrix():

            db_pivot = dbnomics_df.pivot_table(
                index=['year', 'iso'], 
                columns='type', 
                values='value', 
                aggfunc='first'
            ).reset_index()

            # GUARD: Guarantee required macro columns exist in db_pivot
            for required_col in ['exchange_rate', 'inflation', 'hfce']:
                if required_col not in db_pivot.columns:
                    db_pivot[required_col] = np.nan

            # Forward/backward fill exchange_rate and inflation per ISO
            predictor_cols = ['exchange_rate', 'inflation']
            for col in predictor_cols:
                db_pivot[col] = db_pivot.groupby('iso')[col].transform(lambda g: g.ffill().bfill())

            # Masks for Nigeria HFCE OLS Imputation
            nga_mask = db_pivot['iso'] == 'NGA'
            train_mask = nga_mask & db_pivot['hfce'].notna() # 2014-2021
            pred_mask = nga_mask & db_pivot['hfce'].isna()   # 2022-2024
            
            features = ['exchange_rate', 'inflation']

            # Training and Imputing
            if train_mask.sum() > 0 and pred_mask.sum() > 0:
                X_train = db_pivot.loc[train_mask, features]
                y_train = db_pivot.loc[train_mask, 'hfce']
                X_pred = db_pivot.loc[pred_mask, features]

                # Fit OLS Regression
                model = LinearRegression()
                model.fit(X_train, y_train)

                # Impute predicted HFCE values directly back into db_pivot for 2022-2024
                db_pivot.loc[pred_mask, 'hfce'] = model.predict(X_pred)
                
                print("Successfully imputed missing 2022-2024 HFCE data using OLS.")
                
            merged_df = pd.merge(uncom_df, db_pivot, on=['year', 'iso'], how='inner')
            if 'hfce' in merged_df.columns: 
                merged_df['hfce'] = merged_df['hfce'].fillna(merged_df['hfce'].mean())
            
            if merged_df.empty:
                raise RuntimeError("Data integrity failure: Inner join yielded 0 rows.")

            self.df = merged_df
            print(f"-> Matrix synchronized successfully! Matrix shape: {self.df.shape}")
        except Exception as e:
            raise RuntimeError(f"Data synchronization failed: {e}")
        
    def meta_clean(self): 
        if self.df is None or self.df.empty:
            return pd.DataFrame()
        
        df_cleaned = self.df.drop(columns=self.metadata_cols, errors='ignore').copy()
        df_cleaned = df_cleaned.dropna(axis=1, how='all')
        
        non_zero_cols = df_cleaned.loc[:, (df_cleaned != 0).any(axis=0)].columns
        df_cleaned = df_cleaned[non_zero_cols]
        
        return df_cleaned  # Return the cleaned subset instead of overwriting self.df

    def run_stats(self):
        print("\nRunning full analysis:")
        if self.df.empty:
            print("Error: No matrix data present inside the engine to analyse.")
            return None
        
        print("\n--- MERGED DATA ft. First 20 rows ---")
        print(f"Dimensions: {self.df.shape}")
        print(self.df.head(20))
        
        self.meta_clean()
        
        df = self.df.copy()
        metadata = ['typecode', 'freqcode', 'iso']        
        df = df.drop(columns=metadata, errors='ignore')
        df = df.select_dtypes(include=[np.number])
        

        print("\n--- Data Types ---")
        print(self.df.dtypes)
        print(self.df.info())
        stats_summary = df.describe()
        stats_summary.loc['var'] = df.var(numeric_only=True)
        stats_summary.loc['skew'] = df.skew(numeric_only=True)
        print(stats_summary)
        return stats_summary   # individual matrix then combined matrix
    
    def run_corr(self):
        df = self.meta_clean()
        if df.empty:
            return None
       
        energy_cols = [c for c in df.columns if any(x in c for x in ['primaryvalue', 'qty', 'fobvalue', 'cifvalue'])]
        macro_cols = ['inflation', 'exchange_rate', 'hfce']
        target_cols = [col for col in macro_cols if col in df.columns]
        
        if energy_cols:
            print("\n=== UNCOM TRADE CORRELATION ===")
            print(df[energy_cols].apply(pd.to_numeric, errors='coerce').corr())
            
        if target_cols:
            print("\n=== DBN MACROECONOMIC CORRELATION ===")
            print(df[target_cols].apply(pd.to_numeric, errors='coerce').corr())

        if target_cols and energy_cols:
            print("\n=== COMBINED CORRELATION MATRIX ===")
            combined_cols = list(set(energy_cols + target_cols))
            
            corr_df = df[combined_cols].apply(pd.to_numeric, errors='coerce')
            corr_matrix = corr_df.corr()
            print(corr_matrix)
            results = self.speartests()
            return corr_matrix, results
        return None
       
    def speartests(self):
        
        if self.df is None or self.df.empty:
            return {}
        
        if 'altqty' in self.df.columns and 'qty' in self.df.columns:
            self.df['altqty'] = self.df['altqty'].replace(0, np.nan)
            self.df['qty_ratio'] = self.df['qty'] / self.df['altqty'] 
            
        if 'inflation' in self.df.columns and 'exchange_rate' in self.df.columns:
            self.df['stability_ratio'] = (
            self.df['inflation'] / self.df['exchange_rate']
        )
        
        grouped = self.df.groupby('iso')
        self.df['altqty'] = self.df['altqty'].replace(0, float('nan'))
        self.df['qty_ratio'] = self.df['qty'] / self.df['altqty']
        results = {} 
        print("\n--- SPEARMAN CORRELATION & VARIATION TESTS---")

        # highlight the ISO / country code per iteration and derive quantity \
            
        for iso, subset in grouped:   
            print(f"\n--- COUNTRY: {iso} ---")
                                                                                                                                                
            val = subset['primaryvalue'].corr(subset['exchange_rate'], method='spearman')
            print(f"Spearman - Primary Value vs Exchange Rate ({iso}): {val:.4f}")
            results[f'Spearman - Primary Value vs Exchange Rate ({iso}): '] = round(val, 4)
        
        # coefficient variation calculations
            exchange = subset['exchange_rate']
            qty_ratio = subset['qty_ratio'] # derived value
            if exchange.empty:
                results[f'Coefficient of Variation - Exchange Rate ({iso}): '] = None
                print(f"Warning: Exchange rate data for {iso} is insufficient for CV calculation.")
            else:
                var = (qty_ratio.std() / exchange.mean()) * 100
                print(f"Coefficient of Variation - Qty Ratio + Exchange Rate ({iso}): {var:.4f}")
                results[f'Coefficient of Variation - Qty Ratio + Exchange Rate ({iso}): '] = round(var, 4)

            
            # elasticity calculations via log-log regression
            inflation = subset['inflation']
            qty_pct = qty_ratio.pct_change()

            if inflation.empty or qty_pct.empty or inflation.sum() == 0:
                results[f'Elasticity - Quantity vs Inflation ({iso}): '] = None
                print(f"Warning: Inflation data for {iso} is insufficient for elasticity calculation.")
            else:
                df_log = pd.DataFrame({
                    'y': np.log(qty_pct + 1), 
                    'x': np.log(inflation + 1)
                }).replace([np.inf, -np.inf], np.nan).dropna() # aligned log features and drop invalid/inf rows

                
                if len(df_log) > 1 and df_log['x'].var() > 0:
                    elast_final = np.polyfit(df_log['x'], df_log['y'], deg=1)[0] # creates a linear (fit +) regression model and returns the slope (elasticity)
                else:
                    elast_final = 0.0 # Calculating true log-log regression slope (OLS) instead of point division

                print(f"Elasticity - Quantity vs Inflation ({iso}): {elast_final:.4f}") # fix elasticity with log-log regression
                results[f'Elasticity - Quantity vs Inflation ({iso}): '] = round(elast_final, 4)
            
            # Stability Ratio: Inflation : Exchange Rate
            if 'stability_ratio' in subset:
                iso_stability_mean = subset['stability_ratio'].mean()

                if pd.notna(iso_stability_mean):
                    print(f'Stability Ratio - Inflation : Exchange Rate ({iso}): {iso_stability_mean:.4f}')
                    results[f'Stability Ratio - Inflation : Exchange Rate ({iso})'] = round(iso_stability_mean, 4)
                else:
                    print(f'Warning: Stability Ratio for {iso} contains only NaN values.'
                    )
                    results[f'Stability Ratio - Inflation : Exchange Rate ({iso})'] = None
            else:
                print(f'Warning: Required columns for Stability Ratio calculation are missing for {iso}.')
                results[f'Stability Ratio - Inflation : Exchange Rate ({iso})'] = (None)
                    

        return results
    # END OF FIRST HALF 

 # Calculations - guided with Symbolic Regression + OLS
 
 # Energy Equity Score Gap (consumer spending + energy value(s) as key inds)
    def energy_equity_gap(self):
        
        if self.df is None or self.df.empty or 'hfce' not in self.df.columns:
            print("Warning: 'hfce' column missing. Skipping Energy Equity Gap analysis.")
            return None
        
        # Built actual definitions and the actual EES for SR to reference then derive a formula for - the features array below
        # inflation is used as a fallback target if stability_ratio is not available, ensuring the model can still be trained.
        
        target_col = 'stability_ratio' if 'stability_ratio' in self.df.columns else 'inflation' 
        
        features = ['primaryvalue', 'qty_ratio', 'hfce', 'inflation'] # Feature engineering finding detrived HFCE backed formula
        active_features = [col for col in features if col in self.df.columns and col != target_col]
        
        # Ensure columns exist and drop NaNs
        req_cols = active_features + [target_col]
        valid_df = self.df.dropna(subset=req_cols).copy()
        if valid_df.empty:
            print("Warning: No valid data available for Symbolic Regression analysis.")
            return None

        X = valid_df[active_features].values
        Y = valid_df[target_col].values
        
        # Running Symbolic Regression to derive dynamic formula
        sr = SymbolicRegressor(
            population_size=300, # Keep population size moderate to accommodate to db size x future dashboard lag
            generations=350, # Generations repeats the evolution process to refine the model
            max_samples=0.8,
            init_depth=(2,5),        # shorten range of formula depth for ux
            function_set=['add', 'sub', 'mul', 'div', 'log'], # operational limits for user experience (+. -, x, /)
            parsimony_coefficient=0.005,
            random_state=42 # reproducibility of results  
        )
        sr.fit(X, Y)

        # Applying derived SR expression to compute Energy Equity Score
        valid_df['stability_score'] = sr.predict(X)
        
        # further extend and perform symbolic regression to fully encapsulate Energy Equity rather than Currency Stability Ratio (CSR) as a proxy for EES

        # Compute Trilateral Score Gap (China vs Nigeria/Ghana - ESS)
        chn_score = valid_df[valid_df['iso'] == 'CHN']['stability_score'].mean()
        nga_score = valid_df[valid_df['iso'] == 'NGA']['stability_score'].mean()
        gha_score = valid_df[valid_df['iso'] == 'GHA']['stability_score'].mean() # StS will be a placeholder for EES; continue

        parsed_sr = self.parse_sr(sr._program)
        
        gap_results = {
            'SR_Formula': str(parsed_sr) if parsed_sr is not None else "Parsing failed",
            'CHN_Score': round(float(chn_score), 4),
            'NGA_Score': round(float(nga_score), 4),
            'GHA_Score': round(float(gha_score), 4),
            'China_WestAfrica_Gap': round(float(chn_score - np.nanmean([nga_score, gha_score])), 5)
        }
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(features) # fit and transformed in accordance to features

        df_scaled = pd.DataFrame(X_scaled, columns=features) # converted numpy array back to DataFrame for easier downstream processing and visualization

        return gap_results, df_scaled
    
    def parse_sr(self, sr_expression):
        # Convert the symbolic regression expression to a string based sympy expression
        raw_str = str(sr_expression) 
    
        # Map gplearn string operators to SymPy mathematical operations
        local_dict = {
            'add': lambda a, b: a + b,
            'sub': lambda a, b: a - b,
            'mul': lambda a, b: a * b,
            'div': lambda a, b: a / b,
            'log': sp.log, # respectively limits till here
            'sqrt': sp.sqrt,
            'abs': sp.Abs,
            'neg': lambda a: -a,
            'inv': lambda a: 1 / a
        }
        
        # Map indexed variables (X0, X1, ...) to actual dataframe column names
        for i, name in enumerate(self.feature_names):
            local_dict[f'X{i}'] = sp.Symbol(name)
            
        try:
            sympy_expr = eval(raw_str, {"__builtins__": None}, local_dict)
            return sympy_expr
        except Exception as e:
            print(f"Error parsing symbolic regression expression: {e}")
            return None