import pandas as pd
import numpy as np
from datacleanse import DataCleaner, Fetcher
import scipy.stats as stats
import statsmodels.api as sm
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
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
       
        energy_cols = [c for c in df.columns if any(x in c for x in ['primaryvalue', 'qty', 'fobvalue', 'netwgt', 'cifvalue'])]
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
            self.df['qty_ratio'] = self.df['qty'] / self.df['altqty'] # unit based calculation for elasticicity
        
        grouped = self.df.groupby('iso')
        self.df['altqty'] = self.df['altqty'].replace(0, float('nan'))
        self.df['unit_value'] = (self.df['primaryvalue'] / self.df['netwgt'].replace(0, np.nan))    
        results = {} 
        print("\n--- SPEARMAN CORRELATION & VARIATION TESTS---")

        # highlight the ISO / country code per iteration and derive quantity \
            
        for iso, subset in grouped:   
            print(f"\n--- COUNTRY: {iso} ---")
                                                                                                                                                
            val = subset['primaryvalue'].corr(subset['exchange_rate'], method='spearman')
            print(f"Spearman - Primary Value vs Exchange Rate ({iso}): {val:.4f}")
            results[f'Spearman - Primary Value vs Exchange Rate ({iso}): '] = round(val, 4)
        
            # unit value 
            net_wgt = subset['netwgt'] 
            pv = subset['primaryvalue'] # derived value
            if pv.dropna().empty or net_wgt.sum() == 0:
                results[f'Unit Value Primary Val : Net Weight ({iso}): '] = None
                print(f"Warning: Data for {iso} is insufficient for UV calculation.")
            else:
                unit_val = subset['unit_value'].replace(0, np.nan)
                print(f"Unit Value Primary Val : Net Weight ({iso}): {unit_val.mean():.4f}")
                results[f'Unit Value Primary Val : Net Weight ({iso}): '] = round(unit_val.mean(), 4)

            
            # elasticity calculation | hybrid log log regression + division method
            inflation = subset['inflation'].replace(0, np.nan)
            qty_ratio = subset['qty_ratio'].replace(0, np.nan)
            
            valid_data = pd.concat([qty_ratio, inflation], axis=1).dropna()
            if inflation.empty or valid_data.empty or inflation.sum() == 0:
                results[f'Elasticity - Quantity vs Inflation ({iso}): '] = None
                print(f"Warning: Data for {iso} is insufficient for elasticity calculation.")
            
            if len(valid_data) >= 3:
                log_inf = np.log(valid_data['inflation'])
                log_qty = np.log(valid_data['qty_ratio'])
                X = sm.add_constant(log_inf)
                model = sm.OLS(log_qty, X).fit()
                
                elast = model.params['inflation']
                residuals = model.resid # residuals are like the standard deviation relative to the elasticity relationship
                print(f"Elasticity - Quantity vs Inflation ({iso}): {elast:.4f}")
                print(f"Residuals: {residuals.describe()}")
                results[f'Elasticity - Quantity vs Inflation ({iso}): '] = round(elast, 4)
                results[f'Residuals - Quantity vs Inflation ({iso}): '] = residuals.tolist()
            
            # Covariance
            pass
            
            
        return results
    # END OF FIRST HALF 

 
 
 # Calculations - guided with PCA + OLS
 # Energy Equity Score Gap (consumer spending + energy value(s) as key inds)
 
class EnergyEquityScore:
    def __init__(self, df):
        self.df = df
        self.features = ['netwgt', 'inflation', 'exchange_rate', 'primaryvalue'] # Store feature names for Symbolic Regression reminiscent weighting
        self.feature_names = [col for col in self.features if col in self.df.columns]
        target_col = None
                    
    
    def run_pca(self, n_components=2, target_col='hfce'):
        if self.df is None or self.df.empty:
            return None
        
        active_features = [col for col in self.features if col in self.df.columns] # = feature_names
        
        if not active_features:
            print("Warning: No valid PCA features found.")
            return None

        # Require target
        if target_col not in self.df.columns:
            print(f"Warning: Target '{target_col}' missing.")
            return None
        
        req_cols = active_features + [target_col]
        valid_df = self.df.dropna(subset=req_cols).copy()

        if valid_df.empty:
            print("Warning: No valid rows available for PCA.")
            return None
        
        # Principal Component Analysis based on briding EES gap
        X = valid_df[active_features]
        
        X = valid_df[active_features].copy()
        for feature in ("netwgt", "primaryvalue"):
            if feature in X.columns:
                X[feature] = np.log1p(X[feature].clip(lower=0))        
        Y = valid_df[target_col]

        # Standardize the data for PCA
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        scaled = pd.DataFrame(X_scaled, columns=active_features, index=valid_df.index)
        
        # Fit on training data AND transform it
        pca = PCA(n_components=n_components)
        X_pca = pca.fit_transform(X_scaled)
        
        loadings = pd.DataFrame(
        pca.components_.T,
        index=active_features,
        columns=[f'PC{i + 1}' for i in range(n_components)])

        print("\n--- PCA LOADINGS ---")
        print(loadings)

        print("\n--- EXPLAINED VARIANCE ---")
        for i, variance in enumerate(pca.explained_variance_ratio_):
            print(f"PC{i + 1}: {variance:.4f} " f"({variance * 100:.2f}%)")
            
        pca_results = {
        'pca_model': pca,
        'scaler': scaler,
        'scaled_data': scaled,
        'pca_scores': X_pca,
        'loadings': loadings,
        'explained_variance': pca.explained_variance_ratio_,
        'feature_names': active_features }

        return pca_results, scaled
        
    
    def energy_equity_gap(self, n_components=2):
        if self.df is None or self.df.empty or 'hfce' not in self.df.columns:
                print("Warning: 'hfce' column missing. Skipping Energy Equity Gap analysis.")
                return None
        
        # create the Energy Equity Score + Gap based on metrics above | respective Elec. and Solar sccores
        # return gap_results, scaled
    
    
    def parse_sr(self, sr_expression):
        # Convert the symbolic regression like expression to a string based sympy expression
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
    
    def json_dc(self): 
        return { 
            "pc1": None,
            "pc2": None,
            "energy_score": None,
            "economic_score": None,
            "net_ees": None,
            "weights": None            } # placeholders