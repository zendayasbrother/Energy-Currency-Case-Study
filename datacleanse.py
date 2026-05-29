import pandas as pd
import numpy as np
import psycopg2
import requests
import json

class DataCleaner:
    def __init__(self, api_url, api_key, countries):
        countries = countries.replace(" ", "")
        
        params = {
            "typeCode": "C",          # Commodities
            "freqCode": "A",          # Annual
            "clCode": "HS",          
            "reporterCode": countries, 
            "partnerCode": "0",       # World
            "period": "2023",
            "cmdCode": "2709"         # Electricity and Solar
        }
        
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        response = requests.get(api_url, params=params, headers=headers)
        
        if response.status_code == 200:
            self.df = pd.DataFrame(response.json())
            print("API successfuly ingested")
            self.standardize_columns()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            raise Exception("API request failed")
        response = requests.get(api_url)
        

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


        print("\n--- First 10 rows ---")
        print(self.df.head(10))

        print("\n--- Data Types ---")
        print(self.df.dtypes)
        print(self.df.info())
        print(self.df.describe())

        pass # Sub function ofr formatting - prints the formatted version via lamda function
        pass # Save to database for ease. access via env
        
        