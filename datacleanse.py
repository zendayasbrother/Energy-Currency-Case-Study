import pandas as pd
import numpy as np
import psycopg2
import os
import requests
import json
import time
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from dbnomics import fetch_series 
import importlib.metadata
    
load_dotenv()

class DataCleaner:
    def __init__(self, api_url, api_key, countries, db_path):
        self.engine = create_engine(db_path)
        self.api_key = api_key
        self.api_url = api_url
        self.db_path = db_path
        self.name = "bilateral_trade"
        self.df = []
        self.countries = countries


    def fetch_api(self, countries):
        for country in countries:
            params = {
                "reporterCode": str(country), # Ensure each request is handled individually
                "partnerCode": "0",
                "period": "2023",
                "cmdCode": "2709"
            }
            
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            
            try:
                response = requests.get(self.api_url, params=params, headers=headers)
                
                if response.status_code == 200:
                    result = response.json()
                    data = result.get('dataset') or result.get('data')
                    
                    if data:
                        self.df.append(pd.json_normalize(data))
                        print(f"Successfully fetched {country}")
                    else:
                        print(f"No data found for {country}")
                elif response.status_code == 429:
                    print("Rate limit hit, sleeping...")
                    time.sleep(5) # Wait 5 seconds before retrying
                else:
                    print(f"Error {country}: {response.status_code} - {response.text}")
            
            except Exception as e:
                print(f"Failed {country}: {e}")
                
            time.sleep(1.1) # Respect API rate limits (1 request/sec)

        if self.df:
            self.df = pd.concat(self.df, ignore_index=True)
            self.standardize_columns()
        else:
            raise Exception("No data could be retrieved.")
    
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


        print("\n--- Data Audit ---")
        print(self.df.head(10))
        print(self.df.tail(5))
        print("\n--- First 10 rows ---")
        print(self.df.head(10))
        print(self.df.shape)
        self.df = self.df.fillna(0)

        print("\n--- Data Types ---")
        print(self.df.dtypes)
        print(self.df.info())
        print(self.df.describe())

        pass # Sub function for formatting - prints the formatted version via lamda function
    
    # function(s) to save / push api to database for ease. access via env
    def connect_database(self, db_path=None):
        if self.df is None or self.df.empty:
            print("No data to push.")
            return

        try:
            with self.engine.begin() as conn:
                self.schema = 'Trade Intelligence'
                
                self.df.to_sql(
                    name = self.name,
                    con = conn,
                    schema = self.schema,
                    if_exists = "replace",
                    index = False
                )
                
            print(f"Success: Data pushed to {self.schema}.{self.name}")
        except Exception as e:
            print(f"CRITICAL ERROR during database push: {e}")
            
    """ Repeat the same ETL process but with DBNomices and monetary data
    in a modular manner, then test it """

class Fetcher(DataCleaner): 
    def __init__(self, db_path):
        super().__init__(None, None, None, db_path)
        self.name = "Currency_Stability"
        self.curr_inf = [
                'WorldBank/WDI/FP.CPI.TOTL.ZG-GHA',
                'WorldBank/WDI/FP.CPI.TOTL.ZG-NGA',
                'WorldBank/WDI/FP.CPI.TOTL.ZG-CHN'
            ] # inflation (% change)
        
        self.fx = [
                'IMF/IFS/A.GHA.ENDE_XDC_USD_RATE',
                'IMF/IFS/A.NGN.ENDE_XDC_USD_RATE',
                'IMF/IFS/A.CHN.ENDE_XDC_USD_RATE'
            ] # exchange rates
        
    def fetch_all(self):
        # Mapping connection
        data_map = {
            'inflation': self.curr_inf,
            'exchange_rate': self.fx
        }
        
        frame = []
        
        for category, code_list in data_map.items():
            for code in code_list:
                try:
                    # Fetch series return: list, dict, etc
                    result = fetch_series(code)
                    if isinstance(result, pd.DataFrame):
                        df = result
                    else:
                        df = pd.DataFrame(result)
                    
                    df['type'] = category
                    self.df = df 
                    self.standardize_columns()
                    
                    frame.append(self.df)
                except Exception as e:
                    print(f"Error fetching {code}: {e}")
                    
        # Post fetching concatenation
        if frame:
            self.df = pd.concat(frame, ignore_index=True)
            print(f"Successfully ingested {len(frame)} series.")
        else:
            print("No data could be ingested.") # fix whole DBN fetching
        
        
    def clean_data(self): 
        super().clean_data()
        
    def connect_database(self, db_path = None): 
        super().connect_database(db_path)