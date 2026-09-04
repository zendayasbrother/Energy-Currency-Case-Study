from engine import DataEngine
import pandas as pd
import numpy as np
import json
from scipy import stats
import nashpy as nash
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')

class ECModels(DataEngine):
    def __init__(self, df, df_scaled=None):
        super().__init__(cleaner=None, fetcher=None)  
        self.df = df
        self.scaled = df_scaled

    
    def run_pca(self, n_components=2):
        if self.df is None or self.df.empty:
            return None
        
        if self.scaled is None or self.scaled.empty:
            print("Warning: Scaled DataFrame is empty for PCA analysis.")
            return None
        
        target_col = 'stability_ratio' if 'stability_ratio' in self.df.columns else 'inflation'
        
        # Principal Component Analysis based on briding EES gap
        X = self.scaled[self.features]
        Y = self.scaled[target_col]
        X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, random_state=42)

        scaler = StandardScaler()

        # Fit on training data AND transform it
        pca = PCA(n_components=n_components)
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model = LinearRegression()
        model.fit(X_train_scaled, Y_train)
        
        Y_pred = model.predict(X_test)
        
        results = {
            'pca_model': pca,
            'regression_model': model,
            'components': pca.components_,
            'explained_variance': pca.explained_variance_ratio_ # rest of results are in the LR func
        }
        
        return results
        
    def run_linear_regression(self):
        if self.df is None or self.df.empty:
            print("Warning: DataFrame is empty for linear regression analysis.")
            return None

        # Force conversion of all columns to numeric to avoid data type mismatch bugs
        
        clean_df = self.meta_clean()
        
        numeric = clean_df.apply(pd.to_numeric, errors='coerce')
        numeric = numeric.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)
        
        # removed idxmax() to avoid potential issues with constant columns leading to NaN correlations

        if numeric.shape[1] < 2:
            print(f"Warning: Insufficient numeric columns ({numeric.shape[1]}) available for regression.")
            return None
            
        # Compute correlation matrix and safely handle NaNs resulting from constant values
        correlations = numeric.corr().fillna(0)
        corr_values = correlations.values.copy()
        np.fill_diagonal(corr_values, 0)

        correlations = pd.DataFrame(
            corr_values, index=correlations.index, columns=correlations.columns
        )

        if correlations.abs().max().max() == 0:
            print("Warning: All pairwise correlations are zero or undefined.")
            return None

        predictor, target = correlations.abs().stack().idxmax()

        if correlations.loc[predictor, target] == 0:
            print("Warning: Selected predictor and target correlation is zero.")
            return None

        # Filter out rows with missing values for the selected predictor-target pair
        data = numeric[[predictor, target]].dropna()
        if len(data) < 2:
            print(f"Warning: Insufficient matching data rows ({len(data)}) for pair: {predictor} vs {target}.")
            return None

        # Fit the Linear Regression model
        model = LinearRegression().fit(data[[predictor]], data[target])
        
        return {
            'predictor': predictor,
            'target': target,
            'correlation': float(correlations.loc[predictor, target]),
            'coefficient': float(model.coef_[0]),
            'intercept': float(model.intercept_),
            'r_squared': float(model.score(data[[predictor]], data[target])),
            'model': model,
        }
        
    def run_forecasting(self):
        pass # Placeholder for ARIMA, SARIMA, Prophet, etc.
    
    def run_game_theory(self):
        pass # Placeholder for Stackelberg / Game Theory models