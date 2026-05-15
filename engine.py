import pandas as pd
import numpy as np
import wbgapi as wb
import json
from sklearn.linear_model import LinearRegression
from datacleanse import DataCleaner

# DataEngine is a class for orchestrating the math and game theory analysis on the cleaned dataset. It serves as a higher-level interface to the DataCleaner and can be extended with additional methods for specific analyses or visualizations in the future.
class DataEngine:
    def __init__(self, data_source):
        self.data_cleaner = DataCleaner(data_source)

    def process_data(self):
        self.data_cleaner.clean_data()