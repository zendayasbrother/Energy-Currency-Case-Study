import pandas as pd
import numpy as np
import psycopg2
import os
import requests
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from dbnomics import fetch_series 
import importlib.metadata
    
load_dotenv()

class DataCleaner:
    def __init__(self, api_url, api_key, countries, db_path):
        self.engine = create_engine(db_path)
        self.name = "BilateralTrade"
        self.api_key = api_key
        self.api_url = api_url
        self.db_path = db_path
        self.df = None
        
        if countries is not None:
            countries = countries.replace(" ", "")
        self.countries = countries
    
    def fetch_api(self, countries):
        params = {
            "typeCode": "C",          # Commodities
            "freqCode": "A",          # Annual
            "clCode": "HS",          
            "reporterCode": countries, 
            "partnerCode": "0",       # World
            "period": "2023",
            "cmdCode": "2709"         # Electricity and Solar
        }
        
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        response = requests.get(self.api_url, params=params, headers=headers)
        self.df = None
        
        if response.status_code == 200:
            self.df = pd.json_normalize(response.json()['dataset'])
            self.df = self.df.fillna(0)
            self.standardize_columns()
            print("API successfuly ingested")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            raise Exception("API request failed")
        
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
    def connect_database(self, db_path):
        if db_path:
            conn = psycopg2.connect(os.getenv("DB_PATH")) # Use your connection string here
            cur = conn.cursor()
            with open(db_path, 'r') as f:
                cur.execute(f.read())
            conn.commit()
            cur.close()
            conn.close()
        
        if self.df is None or self.df.empty:
            print("No data to push.")
            return
        
        try:
            # Idempotency with it detecting + removing duplicates every single run
            with self.engine.connect() as conn:
                query = text(f"""DELETE FROM "{self.name}"
                            WHERE period IN (
                                SELECT period FROM "{self.name}"
                                GROUP BY period 
                                HAVING COUNT(*) > 1
                            )""")
                conn.execute(query)
                conn.commit() 
                
            # Push the API data into a new (created table)
            self.df.to_sql(
                name = "Bilateral_Trade",
                con = self.engine,
                if_exists = "replace",
            )
            print(f"Data successfully pushed to new table: {self.name}")
        except Exception as e:
            print(f"Error reading table: {e}")  #automaticallu update DSR SCRIPT.sql file though
            
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
                    df = fetch_series(code)
                    self.standardize_columns()
                    df['type'] = category
                    frame.append(df)
                except Exception as e:
                    print(f"Error fetching {code}: {e}")
                    
        # Post fetching concatenation
        if frame:
            self.df = pd.concat(frame, ignore_index=True)
            print(f"Successfully ingested {len(frame)} series.")
        
        
    def clean_data(self): 
        super().clean_data()
        
    def connect_database(self, db_path = None): 
        super().connect_database(db_path)