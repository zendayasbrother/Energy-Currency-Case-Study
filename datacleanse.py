import pandas as pd
import numpy as np
from dbnomics import fetch_series
import requests
import json
import time
from sqlalchemy import create_engine, text

class DataCleaner:
    def __init__(self, db_path=None, api_url=None, api_key=None, countries=None):
        self.engine = create_engine(db_path) if db_path else None
        self.api_key = api_key
        self.api_url = api_url
        self.db_path = db_path
        self.name = "bilateral_trade"
        self.df = pd.DataFrame()
        self.countries = countries

    def fetch_api(self, countries):
        print("Executing API ingestion from UNCOM Trade...")
        frames = []
        for country in countries:
            params = {
                "reporterCode": str(country), 
                "partnerCode": "0",
                "period": "2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024",
                "cmdCode": "854143,271600" # solar, electricity
            }
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            try:
                response = requests.get(self.api_url, params=params, headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    data = result.get("dataset") or result.get("data")
                    if data:
                        df_temp = pd.json_normalize(data) # flatten the JSON structure
                        country_iso_map = {288: "GHA", 566: "NGA", 156: "CHN"}
                        df_temp['iso'] = country_iso_map.get(country, "UNKNOWN")
                        frames.append(df_temp)
                        print(f"Successfully fetched {country}")
                    else:
                        print(f"No data found for {country}")
                elif response.status_code == 429:
                    print("Rate limit hit, sleeping...")
                    time.sleep(5)
                else:
                    print(f"Error {country}: {response.status_code}")
            except Exception as e:
                print(f"Failed {country}: {e}")
            time.sleep(1.1)

        if frames:
            self.df = pd.concat(frames, ignore_index=True)
            self.standardise_columns()
            self.clean_data()
            return self.df
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
        print("\n--- Data Audit ft. First 10 rows ---")
        print(f"Initial Dimensions: {self.df.shape}")
        print(self.df.head())
        
        print("\n--- Data Types ---")
        print(self.df.dtypes)
        print(self.df.info())
        
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        self.df[numeric_cols] = self.df[numeric_cols].fillna(0)
        
        metadata_cols = [
            'refperiodid', 'refmonth', 'partnercode', 'partner2code', 
            'motcode', 'qtyunitcode', 'altqtyunitcode', 'legacyestimationflag'
        ]
        
        self.df = self.df.drop(columns=metadata_cols, errors='ignore') # removes redundant metadata columns
        self.df = self.df.dropna(axis=1, how='all') # also drops columns that are entirely NaN
        self.df = self.df.loc[:, (self.df != 0).any(axis=0)] 
        print(f"Post Audit and Clean: {self.df.shape}")
        
        return self.df

        pass # Sub function for formatting - prints the formatted version via lamda function

    def connect_database(self, db_path = None):
        if self.df is None or self.df.empty:
            print("No data to push.")
            return
        try:
            with self.engine.begin() as conn:
                temp_name = f"{self.name}_temp" # staging table for later upsert (update or insert) command
                self.df.to_sql(temp_name, con=conn, schema='Trade Intelligence', if_exists="replace", index=False)
                
                upsert_sql = f"""
                    INSERT INTO "Trade Intelligence".{self.name} 
                    SELECT * FROM "Trade Intelligence".{temp_name}
                    ON CONFLICT (period, partnercode) -- Set your actual PKs here
                    DO UPDATE SET 
                        primaryvalue = EXCLUDED.primaryvalue,
                        qty = EXCLUDED.qty;
                    DROP TABLE "Trade Intelligence".{temp_name};"""
                    
                conn.execute(text(upsert_sql))
            print(f"Success: Upsert completed for {self.name}")
        except Exception as e:
            print(f"CRITICAL ERROR during database upsert: {e}")

class Fetcher(): 
    def __init__(self, db_path):
        self.db_path = db_path
        self.engine = create_engine(db_path) if db_path else None
        self.name = "Currency_Stability"  
        self.df = pd.DataFrame()

        
    def fetch_all(self): 
        print(f"Executing batch ingestion from DB Nomics...")
        try:
            wb_df = fetch_series(provider_code='WB', dataset_code='WDI',
                dimensions={'frequency': ['A'], # annual
                            'country': ['GHA', 'NGA', 'CHN'], # country isos
                            'indicator': ['FP.CPI.TOTL.ZG']} # inflation per consumer price index
            )
            imf_df = fetch_series(provider_code='IMF', dataset_code='IFS',
                dimensions={'FREQ': ['A'], 
                            'REF_AREA': ['GH', 'NG', 'CN'], 
                            'INDICATOR': ['ENDE_XDC_USD_RATE']} # exchange rate in USD
            )

            if wb_df.empty and imf_df.empty:
                raise Exception("DB Nomics returned an empty dataset for both providers.")
                
            fetched_df = pd.concat([wb_df, imf_df], ignore_index=True) # sticks into master table

            df_cleaned = pd.DataFrame({
                "period": fetched_df["period"],
                "value": pd.to_numeric(fetched_df["value"], errors="coerce"),
                "series_code": fetched_df["series_code"],
            })

            df_cleaned["type"] = df_cleaned["series_code"].apply(
                lambda x: "inflation" if "FP.CPI" in str(x) else "exchange_rate"
            )
            
            df_cleaned["year"] = pd.to_datetime(df_cleaned["period"]).dt.year
            df_cleaned = df_cleaned[df_cleaned["year"].between(2014, 2024)]
            
            df_cleaned["iso"] = "UNKNOWN"
            df_cleaned.loc[df_cleaned["series_code"].str.contains("GHA|GH"), "iso"] = "GHA"
            df_cleaned.loc[df_cleaned["series_code"].str.contains("NGA|NG"), "iso"] = "NGA"
            df_cleaned.loc[df_cleaned["series_code"].str.contains("CHN|CN"), "iso"] = "CHN"

            self.df = df_cleaned
            print(f"-> Successfully synchronized series from WB and IMF.")
            self.standardise_columns()
            self.clean_data()
            return self.df
        except Exception as e:
            raise Exception(f"Critical pipeline error: {e}")
        
    def clean_data(self):
        print("\n--- Data Audit ft. First 10 rows ---")
        print(f"Initial Dimensions: {self.df.shape}")
        print(self.df.head())
        
        print("\n--- Data Types ---")
        print(self.df.dtypes)
        print(self.df.info())
        
        self.df = self.df.dropna(axis=1, how='all')
        self.df = self.df.loc[:, (self.df != 0).any(axis=0)]
    
        print(f"Post Audit and Clean: {self.df.shape}")
        
        return self.df
        
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
    
    def connect_database(self): 
        if self.df is None or self.df.empty:
            print("No data to push.")
            return
        try:
            with self.engine.begin() as conn:
                temp_name = f"{self.name}_temp"
                self.df.to_sql(temp_name, con=conn, schema='Trade Intelligence', if_exists="replace", index=False)
                
                upsert_sql = f"""
                    INSERT INTO "Trade Intelligence".{self.name} 
                    SELECT * FROM "Trade Intelligence".{temp_name}
                    ON CONFLICT (period, country_code) -- Match your PK
                    DO UPDATE SET 
                        exports_to_chn = EXCLUDED.exports_to_chn;
                    DROP TABLE "Trade Intelligence".{temp_name};
                """
                conn.execute(text(upsert_sql))
            print(f"Success: Upsert completed for {self.name}")
        except Exception as e:
            print(f"CRITICAL ERROR during database upsert: {e}")
            
            
    # MOVE THIRD SYNCING MATRIX CLASS HERE FROM ENGINE
        
    def json_dc(): 
        
        {"api_settings": {
            "uncom_base_url": "https://api.comtrade.un.org/v1",
            "cmd_codes": ["854143", "271600"],
            "periods": "2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024"
        },
        
        "countries": {
            "reporting": [288, 566, 156],
            "iso_mapping": {
            "288": "GHA",
            "566": "NGA",
            "156": "CHN"
            }
        },
        
        "pipeline": {
            "target_table": "bilateral_trade",
            "schema": "Trade Intelligence",
            "clean_nulls": True
        }
            }