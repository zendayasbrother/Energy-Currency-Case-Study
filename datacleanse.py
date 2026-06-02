import pandas as pd
import numpy as np
import psycopg2
from dbnomics import fetch_series
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy import create_engine
import os
import requests
import json
    
load_dotenv()

class DataCleaner:
    def __init__(self, api_url, api_key, countries, db_path):
        self.engine = create_engine(db_path)
        self.name = "bilateral_trade" # Define this here!
        self.df = None
        self.df2 = fetch_series("WB/WDI/NY.GDP.MKTP.CD")
        countries = countries.replace(" ", "")
        
        params = {
            "typeCode": "C",          # Commodities
            "freqCode": "A",          # Annual
            "clCode": "HS",          
            "reporterCode": countries.replace(" ", ""), 
            "partnerCode": "0",       # World
            "period": "2023",
            "cmdCode": "2709"         # Electricity and Solar
        }
        
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        response = requests.get(api_url, params=params, headers=headers)
        self.df = None
        
        if response.status_code == 200:
            self.df = pd.json_normalize(response.json()['dataset'])
            self.df = self.df.fillna(0)
            self.standardize_columns()
            print("API successfuly ingested")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            raise Exception("API request failed")
        
        
        if response.status_code == 200:
            self.df = pd.json_normalize(response.json()['dataset'])
            print("API successfuly ingested")
        else:
            self.df = pd.DataFrame(response.json())
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
    def connect_database(self, db_path = None):
        
        if db_path:
            conn = psycopg2.connect(os.getenv("DATABASE_URL")) # Use your connection string here
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
            # Idempotency with it removing duplicates every single run
            with self.engine.connect() as conn:
                conn.execute(text(f"DELETE FROM {self.name} WHERE period = 2023"))
                conn.commit() 
                
            # SQL query via pandas to push the API data into a new (created table)
            self.df.to_sql(
                name = "bilateral_trade",
                con = self.engine,
                if_exists = "append",
                if_exists = "replace",
                index = False
            )
            print(f"Data successfully pushed to new table: {self.name}")
        except Exception as e:
            print(f"Error reading table: {e}")
            
    