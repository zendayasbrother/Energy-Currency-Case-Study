from engine import DataEngine
import pandas as pd
import numpy as np
import json
from scipy import stats
import nashpy as nash
from engine import DataEngine
from sklearn.linear_model import LinearRegression 
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')

# Plots different mathematical demos, and visualises complex relationships (game theory)

class ECModels():
    def __init__(self, countries):
        engine = DataEngine(cleaner=None, fetcher=None)  # Placeholder for cleaner and fetcher#
        self.df = engine.sync_matrix(countries)  # Synchronize the matrix for the specified countries
        
    def run_linear_regression(self):
        if self.df is None or self.df.empty:
            return None

        numeric = self.df.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)
        numeric = numeric.dropna(axis=1, how='all')
        if numeric.shape[1] < 2:
            return None

        correlations = numeric.corr()
        np.fill_diagonal(correlations.values, 0)
        predictor, target = correlations.abs().stack().idxmax()
        if correlations.loc[predictor, target] == 0:
            return None

        data = numeric[[predictor, target]].dropna()
        if len(data) < 2:
            return None

        model = LinearRegression().fit(data[[predictor]], data[target])
        return {
            'predictor': predictor,
            'target': target,
            'correlation': correlations.loc[predictor, target],
            'coefficient': model.coef_[0],
            'intercept': model.intercept_,
            'r_squared': model.score(data[[predictor]], data[target]),
            'model': model,
        }
    
    def run_game_theory(self):
        pass # Stacklberg model 
