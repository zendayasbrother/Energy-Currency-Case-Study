import pandas as pd
import numpy as np
import wbgapi as wb
import json
from sklearn.linear_model import LinearRegression
from datacleanse import DataCleaner

class DataEngine:
    def __init__(self, data_source):
        self.data_cleaner = DataCleaner(data_source)

    def process_data(self):
        self.data_cleaner.clean_data()