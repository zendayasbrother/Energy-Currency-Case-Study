import pandas as pd
import numpy as np
from dotenv import load_env
import os
import requests
import json

class DataCleaner:
    def __init__(self, data_source):
        load_env()
        api_key = os.getenviron.get('UNCOM_KEY') # get API
        if isinstance(data_source, pd.DataFrame):
            data_source = api_key
            self.df = data_source
            print("DataFrame ingested from API successfully.")
        else:
            self.df = pd.read_json(data_source)
            print(f"File loaded successfully from {data_source}")

        self.standardize_columns()

    def standardize_columns(self):
        self.df.columns = (
            self.df.columns.str.strip()
            .str.replace(' ', '_')
            .str.replace('–', '_')
            .str.replace('-', '_')
            .str.lower()
        )

    def clean_data(self):
        pass
        def formatter(val, row_name):
            if row_name == 'count':
                try: return f"{int(float(val))}"
                except: return val
            try:
                # Stats view follows the 4-digit precision logic
                return f"{float(val):.4g}" if not isinstance(val, str) else val
            except: return val

        pass # Prints the formatted version via lamda function
        
        return self.df
    
    def gen_json(self):
        pass