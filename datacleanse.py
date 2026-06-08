import pandas as pd
import numpy as np
import psycopg2
import os
import requests
import json
import time
from dotenv import load_dotenv
from sqlalchemy import create_engine
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
    def connect_database(self, db_path = None):
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
    def __init__(self, dbn_url, db_path):
        super().__init__(None, None, None, db_path)
        self.dbn_url = dbn_url
        self.name = "Currency_Stability"
        self.df = []
        self.curr_inf = [
                'WB/WDI/FP.CPI.TOTL.ZG-GH',  # Inflation (% annual) - Ghana
                'WB/WDI/FP.CPI.TOTL.ZG-NG',  # Inflation (% annual) - Nigeria
                'WB/WDI/FP.CPI.TOTL.ZG-CN'   # Inflation (% annual) - China
            ]
        
        # FIXED: Changed 'IMF/IFS/A.GHA...' to the standard 2-digit ISO IMF ledger mapping.
        self.fx = [
                'IMF/IFS/A.GH.ENDE_XDC_USD_RATE',  # Exchange Rate - Ghana
                'IMF/IFS/A.NG.ENDE_XDC_USD_RATE',  # Exchange Rate - Nigeria
                'IMF/IFS/A.CN.ENDE_XDC_USD_RATE'   # Exchange Rate - China
            ]
        
        
    def fetch_all(self):
        dbn_url = self.dbn_url.rstrip('/')
        url = f"{dbn_url}/series"
        
        # Combine strings into unified, qualified path references
        targets = self.curr_inf + self.fx
        params = {"series_ids": ",".join(targets)}
        
        frames = []
        print(f"Executing batch ingestion from DB Nomics registry gateway...")
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"DB Nomics Gateway rejected request with HTTP status: {response.status_code}")

            data = response.json()
            series_data = data.get("series", {})
            docs = series_data.get("docs", [])

            if not docs:
                raise Exception("API Gateway returned an empty registry dataset matching these codes.")

            for doc in docs:
                # Resolve the global identifiers safely from the returned payload mapping
                provider_code = doc.get("provider_code")
                dataset_code = doc.get("dataset_code")
                series_code = doc.get("series_code")
                
                periods = doc.get("period", [])
                values = doc.get("value", [])

                if not periods or not values:
                    continue

                df = pd.DataFrame({
                    "period": periods,
                    "value": values
                })

                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                
                signature = f"{provider_code}/{dataset_code}/{series_code}"
                df["series_code"] = signature
                
                if signature in self.curr_inf:
                    df["type"] = "inflation"
                else:
                    df["type"] = "exchange_rate"

                frames.append(df)
                print(f"-> Successfully synchronized series: {signature}")

        except Exception as e:
            print(f"Pipeline processing failed: {e}")

        if not frames:
            raise Exception("Critical: No matching dataframes resolved from DB Nomics query dimensions.")

        self.df = pd.concat(frames, ignore_index=True)
        self.standardize_columns()
        print(f"Total metrics layers loaded successfully: {len(frames)}")
        
        
    def clean_data(self): 
        super().clean_data()
        
    def connect_database(self, db_path = None): 
        super().connect_database(db_path)