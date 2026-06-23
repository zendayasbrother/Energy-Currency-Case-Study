import pandas as pd
import numpy as np
from dbnomics import fetch_series
import requests
import json
import time
from sqlalchemy import create_engine
    
COUNTRY_REGISTRY = {
    156: {"iso": "CHN", "name": "China"},
    566: {"iso": "NGA", "name": "Nigeria"},
    288: {"iso": "GHA", "name": "Ghana"}
}

COMMODITY_MAP = {
    "854143": "Solar Energy Photovoltaic Cells",
    "271600": "Electrical Energy Grid Flows"
}

IMF_ISO_MAP = {"GH": "GHA", "NG": "NGA", "CN": "CHN"} 

class DataCleaner:
    def __init__(self, db_path, api_url=None, api_key=None, countries=None):
        self.engine = create_engine(db_path) if db_path else None
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
                "reporterCode": str(country), 
                "partnerCode": "0",
                "period": "2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024",
                "cmdCode": "854143,271600" 
            }
            
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            try:
                response = requests.get(self.api_url, params=params, headers=headers)
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
                    print(f"Error {country}: {response.status_code}")
            except Exception as e:
                print(f"Failed {country}: {e}")
            time.sleep(1.1)

        if frames:
            self.df = pd.concat(frames, ignore_index=True)
            self.standardise_columns()
            return self.df
        else:
            raise Exception("No data could be retrieved.")
    
    def standardise_columns(self):
        if self.df is not None and len(self.df.columns) > 0:
            self.df.columns = (
                self.df.columns.str.strip()
                .str.replace(' ', '_')
                .str.replace('–', '_')
                .str.replace('-', '_')
                .str.lower()
            )
        return self.df

    def clean_data(self):
        if self.df.empty:
            return
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        self.df[numeric_cols] = self.df[numeric_cols].fillna(0)
        metadata_cols = [
            'refperiodid', 'refmonth', 'partnercode', 'partner2code', 'motcode', 
            'qtyunitcode', 'grosswgt', 'altqtyunitcode', 'legacyestimationflag'
        ]
        self.df = self.df.drop(columns=metadata_cols, errors='ignore')

    def connect_database(self):
        if self.df is None or self.df.empty:
            print("No data to push.")
            return
        try:
            with self.engine.begin() as conn:
                self.df.to_sql(
                    name=self.name,
                    con=conn,
                    schema='trade_intelligence',
                    if_exists="replace",
                    index=False
                )
            print(f"Success: Data pushed to {self.name}")
        except Exception as e:
            print(f"CRITICAL ERROR during database push: {e}")

class Fetcher(DataCleaner): 
    def __init__(self, db_path):
        super().__init__(db_path=db_path)
        self.name = "Currency_Stability"
        
    def fetch_all(self): 
        print(f"Executing batch ingestion from DB Nomics...")
        try:
            wb_df = fetch_series(provider_code='WB', dataset_code='WDI',
                dimensions={
                    'frequency': ['A'], 
                    'country': ['GHA', 'NGA', 'CHN'], 
                    'indicator': ['FP.CPI.TOTL.ZG']}
            )
            
            imf_df = fetch_series(provider_code='IMF', dataset_code='IFS',
                dimensions={
                    'FREQ': ['A'], 
                    'REF_AREA': ['GH', 'NG', 'CN'], 
                    'INDICATOR': ['ENDE_XDC_USD_RATE']}
            )
            
            if wb_df.empty and imf_df.empty:
                raise Exception("DB Nomics returned empty datasets.")
                
            fetched_df = pd.concat([wb_df, imf_df], ignore_index=True)
            df_cleaned = pd.DataFrame({
                "period": fetched_df["period"],
                "value": pd.to_numeric(fetched_df["value"], errors="coerce"),
                "series_code": fetched_df["series_code"],
            })
            
            df_cleaned["type"] = np.where(df_cleaned["series_code"].str.contains("FP.CPI", na=False), "inflation", "exchange_rate")
            df_cleaned["year"] = pd.to_datetime(df_cleaned["period"]).dt.year
            df = df_cleaned[df_cleaned["year"].between(2014, 2024)]
            
    
            df["iso"] = "UNKNOWN"
            df.loc[df["series_code"].str.contains("GHA|GH"), "iso"] = "GHA"
            df.loc[df["series_code"].str.contains("NGA|NG"), "iso"] = "NGA"
            df.loc[df["series_code"].str.contains("CHN|CN"), "iso"] = "CHN"

            self.df = df
            print(f"-> Successfully synchronized series from WB and IMF.")
            self.standardise_columns()
            return self.df
        except Exception as e:
            raise Exception(f"Critical pipeline error: {e}")
        
    def clean_data(self):
        super().clean_data()

    def connect_database(self):
        super().connect_database() # change to pull mechanism post-engine and COMPOSITION!!
        
    # Future JSON object