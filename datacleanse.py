import pandas as pd
import numpy as np

import requests
import json

class DataCleaner:
    def __init__(self, api_url):
        response = requests.get(api_url)
        if response.status_code == 200: 
            self.df = pd.DataFrame(response.json())
            print("API successfuly ingested")
            self.standardize_columns()
        else:
            print("API didn't load correcftly")
            raise Exception("Failed to load the URL and fetch data. Status code {response.status_code}")

    

    def standardize_columns(self):
        self.df.columns = (
            self.df.columns.str.strip()
            .str.replace(' ', '_')
            .str.replace('–', '_')
            .str.replace('-', '_')
            .str.lower()
        )

    def clean_data(self):
        print(f"Initial Dimensions: {self.df.shape}")


        print("\n--- First 35 Rows ---")
        print(self.df.head(35))

        print("\n--- Data Types ---")
        print(self.df.dtypes())
        print(self.df.info())
        print(self.df.describe())

        pass # Sub function ofr formatting - prints the formatted version via lamda function
        
        return self.df