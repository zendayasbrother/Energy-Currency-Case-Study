from datacleanse import DataCleaner
import pandas as pd
import numpy as np
import wbgapi as wb
import json
from sklearn.linear_model import LinearRegression 
import statsmodels.api as sm
import statsmodels.formula.api as smf
import warnings

warnings.filterwarnings('ignore')


class ECModel:
    def __init__(self, data_source):
        self.data_cleaner = DataCleaner(data_source)

    def process_data(self):
        self.data_cleaner.clean_data()