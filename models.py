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

class ECModels:
    def __init__(self, df, pca_results):
        self.df = df
        self.pca_results = pca_results

        
    def run_linear_regression(self, target="hfce"):
        scores = self.pca_results["pca_scores"]

        data = (
            self.df[[target]]
            .join(scores, how="inner")
            .apply(pd.to_numeric, errors="coerce")
            .dropna()
        )

        features = ["PC1"]  # use PC2 only if you have enough observations
        X = data[features]
        y = data[target]

        model = LinearRegression().fit(X, y)

        return {
            "features": features,
            "target": target,
            "coefficients": dict(zip(features, model.coef_)),
            "intercept": float(model.intercept_),
            "r_squared": float(model.score(X, y)),
            "model": model,
        }
        
    def run_forecasting(self):
        pass # Placeholder for ARIMA, SARIMA, Prophet, etc. | train-test split
    
    def run_game_theory(self):
        pass # Placeholder for Stackelberg / Game Theory models