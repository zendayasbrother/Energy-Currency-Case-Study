from datacleanse import DataCleaner
import pandas as pd
import numpy as np
from scipy import stats
import nashpy as nash
import wbgapi as wb
import json
from sklearn.linear_model import LinearRegression 
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')

# DataEngine is a class for orchestrating the math and game theory analysis on the cleaned dataset. It serves as a higher-level interface to the DataCleaner and can be extended with additional methods for specific analyses or visualizations in the future.
class DataEngine:
    def __init__(self, df):
        super().__init__(self, data_source=None)
        self.df = df