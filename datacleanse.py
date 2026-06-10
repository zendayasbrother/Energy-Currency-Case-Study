import pandas as pd
import numpy as np
from dbnomics import fetch_series
import requests
import json
import time
from sqlalchemy import create_engine
    

class DataCleaner:
    def __init__(self, db_path, api_url=None, api_key=None, countries=None):
        self.engine = create_engine(db_path)
        self.api_key = api_key
        self.api_url = api_url
        self.db_path = db_path
        self.name = "bilateral_trade"
        self.df = pd.DataFrame()
        self.countries = countries


    def fetch_api(self, countries):
        frames = []
        for country in countries:
            params = {
                "reporterCode": str(country), # Ensure each request is handled individually
                "partnerCode": "0",
                "period": "2023",
                "cmdCode": "2709"
            }
            
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            
            try:
                response = requests.get(
                    self.api_url, params=params, headers=headers
                )

                if response.status_code == 200:
                    result = response.json()
                    data = result.get("dataset") or result.get("data")

                    if data:
                        frames.append(pd.json_normalize(data))
                        print(f"Successfully fetched {country}")
                    else:
                        print(f"No data found for {country}")
                elif response.status_code == 429:
                    print("Rate limit hit, sleeping...")
                    time.sleep(5)
                else:
                    print(
                        f"Error {country}: {response.status_code} - {response.text}"
                    )
            except Exception as e:
                print(f"Failed {country}: {e}")

            time.sleep(1.1)

        if frames:
            self.df = pd.concat(frames, ignore_index=True)
            self.standardise_columns()
            self.clean_data()
        else:
            raise Exception("No data could be retrieved.")
    
    def standardise_columns(self):
        if self.df is not None and not self.df.empty:
            self.df.columns = (
                self.df.columns.str.strip()
                .str.replace(' ', '_')
                .str.replace('–', '_')
                .str.replace('-', '_')
                .str.lower()
            )
        
        return self.df

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
    
        # 1. PRE-CLEANING RAW DATASET PREVIEW
        # 2. RUN CLEANING PROCESS
        # 3. POST-CLEANING PROCESSED DATASET PREVIEW
        # FORMAT and FINAL REPORT
   
    
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
    def __init__(self, db_path):
        super().__init__(db_path = db_path)
        self.name = "Currency_Stability"
        self.df = pd.DataFrame() 

    def fetch_all(self): 
        print(f"Executing batch ingestion from DB Nomics...")

        try:
            # WB Fetching via Dimension filters - inflation (annual %)
            wb_df = fetch_series(provider_code='WB', dataset_code='WDI',
                dimensions={
                    'frequency': ['A'],
                    'country': ['GHA', 'NGA', 'CHN'],
                    'indicator': ['FP.CPI.TOTL.ZG']
                }
            )
            
            # IMF Fetching via Dimension filters - exchange rates
            imf_df = fetch_series(provider_code='IMF', dataset_code='IFS',
                dimensions={
                    'FREQ': ['A'],
                    'REF_AREA': ['GH', 'NG', 'CN'],
                    'INDICATOR': ['ENDE_XDC_USD_RATE']
                }
            )

            if wb_df.empty and imf_df.empty:
                raise Exception("DB Nomics returned an empty dataset for both providers.")
                
            fetched_df = pd.concat([wb_df, imf_df], ignore_index=True) # concatenation of both

            df_cleaned = pd.DataFrame(
                {
                    "period": fetched_df["period"],
                    "value": pd.to_numeric(fetched_df["value"], errors="coerce"),
                    "series_code": fetched_df["series_code"],
                }
            )

            df_cleaned["type"] = df_cleaned["series_code"].apply(
                lambda x: (
                    "inflation"
                    if "FP.CPI" in str(x)
                    else "exchange_rate"
                )
            )
            
            self.df = df_cleaned
            print(f"-> Successfully synchronized series from WB and IMF.")
            self.standardise_columns()
            self.clean_data()

        except Exception as e:
            raise Exception(f"Critical pipeline error: {e}")
        
    def clean_data(self):
        super().clean_data()

    def connect_database(self):
        super().connect_database() 
        
    # Future JSON object