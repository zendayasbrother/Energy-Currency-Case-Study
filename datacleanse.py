import pandas as pd
import numpy as np
from dbnomics import fetch_series
import requests
import json
import time
from config import SERIES_MAPPING
from sqlalchemy import create_engine, text
from sklearn.linear_model import LinearRegression

class DataCleaner:
    def __init__(self, db_path=None, api_url=None, api_key=None, countries=None):
        self.engine = create_engine(db_path) if db_path else None
        self.api_key = api_key
        self.api_url = api_url
        self.db_path = db_path
        self.name = "bilateral_trade"
        self.df = pd.DataFrame()
        self.countries = countries
        self.is_from_fallback = False

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
            
            while True:
                try:
                    response = requests.get(self.api_url, params=params, headers=headers)
                    if response.status_code == 200:
                        result = response.json()
                        data = result.get("dataset") or result.get("data")
                        if data:
                            df_temp = pd.json_normalize(data) # flatten the JSON structure
                            country_iso_map = {288: "GHA", 566: "NGA", 156: "CHN"}
                            df_temp['iso'] = country_iso_map.get(int(country), "UNKNOWN")
                            frames.append(df_temp)
                            print(f"Successfully fetched {country}")
                        else:
                            print(f"No data found for {country}")
                        break 
                    elif response.status_code == 429:
                        print("Rate limit hit, sleeping...")
                        time.sleep(5)
                        continue 
                    else:
                        print(f"Error {country}: {response.status_code}")
                        break # Exit retry loop on hard errors
                except Exception as e:
                    print(f"Failed {country}: {e}")
                    break
            time.sleep(1.1)

        if frames:
            self.is_from_fallback = False
            self.df = pd.concat(frames, ignore_index=True)
            self.standardise_columns()
            self.clean_data()
            return self.df
        else:
            try:
                with self.engine.connect() as conn:
                    self.df = pd.read_sql_table(
                        self.name, 
                        con=conn, 
                        schema='Trade Intelligence')
                    if not self.df.empty:
                        print("Warning: API fetch failed. Using existing database data.")
                        self.is_from_fallback = True
                        return self.df
                    else:
                        raise Exception("No existing data available in the database.")
            except Exception as e:
                print(f"Database fetch failed: {e}")
                raise Exception(f"Critical pipeline error: {e}")
    
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
        print(self.df.isnull().sum().reset_index(name = 'Missing Values Counted'))
        
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

    def connect_database(self, db_path = None):
        if self.df is None or self.df.empty:
            print("No data to push.")
            return
        
        active_engine = create_engine(db_path) if db_path else self.engine
        if not active_engine:
            print(f"CRITICAL ERROR: No database engine configured for '{self.name}'.")
            return
        
        try:
            with active_engine.begin() as conn:
                self.df.to_sql(
                    name=self.name, 
                    con=conn, 
                    schema='Trade Intelligence', 
                    if_exists="replace", 
                    index=False
                )
            print(f"Success: Table '{self.name}' written to database.")
        except Exception as e:
            print(f"CRITICAL ERROR during database load: {e}")

class Fetcher(): 
    def __init__(self, db_path):
        self.db_path = db_path
        self.engine = create_engine(db_path) if db_path else None
        self.name = "currency_stability"  
        self.df = pd.DataFrame()
        self.is_from_fallback = False

        
    def fetch_all(self): 
        print(f"Executing batch ingestion from DB Nomics...")
        try:
            wb_df = fetch_series(provider_code='WB', dataset_code='WDI',
                dimensions={'frequency': ['A'], # annual
                            'country': ['GHA', 'NGA', 'CHN'], # country isos
                            'indicator': ['FP.CPI.TOTL.ZG']} # inflation per consumer price index
            )
            for iso in ('GHA', 'NGA', 'CHN'):
                frame = wb_df
                if not frame.empty:
                    frame['iso'] = iso
                    frame['series_code'] = 'FP.CPI.TOTL.ZG'
                    frame['source'] = 'World Bank WDI'
                    frame['is_imputed'] = False
                    wb_df = pd.concat([wb_df, frame], ignore_index=True)
            
            imf_df = fetch_series(provider_code='IMF', dataset_code='IFS',
                dimensions={'FREQ': ['A'], 
                            'REF_AREA': ['GH', 'NG', 'CN'], 
                            'INDICATOR': ['ENDE_XDC_USD_RATE']} # exchange rate in USD
            )
            for iso in ('GH', 'NG', 'CN'):
                frame = imf_df
                if not frame.empty:
                    frame['iso'] = iso
                    frame['series_code'] = 'ENDE_XDC_USD_RATE'
                    frame['source'] = 'World Bank WDI'
                    frame['is_imputed'] = False
                    wb_df = pd.concat([wb_df, frame], ignore_index=True) # filled the NULL blanks in database with the details
            
            # added independent HFCE (USD) dataset for energy-equity calculation

            hfce_frames = []
            for iso in ('GHA', 'CHN'):
                frame = fetch_series(
                    provider_code='WB',
                    dataset_code='WDI',
                    dimensions={
                        'frequency': ['A'],
                        'country': [iso],
                        'indicator': ['NE.CON.PRVT.CD']
                    }
                )
                if not frame.empty:
                    frame['iso'] = iso
                    frame['series_code'] = f'A-NE.CON.PRVT.CD-{iso}'
                    frame['source'] = 'World Bank WDI'
                    frame['is_imputed'] = False
                    hfce_frames.append(frame)

            hfce_df = pd.concat(hfce_frames, ignore_index=True)
            hfce_df['type'] = 'hfce'
            hfce_df['year'] = pd.to_datetime(hfce_df['period']).dt.year

            nga_years = list(range(2014, 2025))
            nga_values_raw = [
                412e9,
                387e9,
                330e9,
                301e9,
                323e9,
                354e9,
                276e9,
                274e9,
            ] + [np.nan, np.nan, np.nan]

            nga_imputed_df = pd.DataFrame({
                "period": [pd.Timestamp(f"{yr}-01-01") for yr in nga_years],
                "value": nga_values_raw,
                "series_code": ["A-NE.CON.PRVT.CD-NGA"] * len(nga_years),
                "type": ["hfce"] * len(nga_years),
                "year": [int(yr) for yr in nga_years],
                "iso": ["NGA"] * len(nga_years),
            })
            
            # Nigeria's supplied HFCE baseline is sourced from Trading Economics.
            # All Nigeria HFCE observations are marked as imputed by project choice;
            # the missing 2022-2024 values are subsequently estimated by OLS in engine.py.
            nga_imputed_df["source"] = "Trading Economics"
            nga_imputed_df["is_imputed"] = True

            # Concatenating all 3 countries into a single DataFrame
            hfce_df = pd.concat([hfce_df, nga_imputed_df], ignore_index=True)
            hfce_df["series_code"] = "A-NE.CON.PRVT.CD-" + hfce_df["iso"]
            hfce_df["value"] = pd.to_numeric(hfce_df["value"], errors="coerce")

            

            if wb_df.empty and imf_df.empty and hfce_df.empty:
                raise Exception("DB Nomics returned an empty dataset for all providers.")
            fetched_df = pd.concat([wb_df, imf_df, hfce_df], ignore_index=True) # sticks into master table

            df_cleaned = pd.DataFrame({
                "period": fetched_df["period"],
                "value": pd.to_numeric(fetched_df["value"], errors="coerce"),
                "series_code": fetched_df["series_code"],
                "source": fetched_df["source"],
                "is_imputed": fetched_df["is_imputed"]
            })

            def assign_type(series_code):
                code_upper = series_code.upper()
                if 'CPI' in code_upper or 'INFLATION' in code_upper:
                    return 'inflation'
                elif 'ENDE_XDC_USD_RATE' in code_upper or 'EXCHANGE' in code_upper:
                    return 'exchange_rate'
                elif 'CON' in code_upper or 'HFCE' in code_upper or 'CONSUMPTION' in code_upper:
                    return 'hfce'
                else:
                    return 'unknown'
                
            df_cleaned["type"] = df_cleaned["series_code"].apply(assign_type)
                                    
            df_cleaned["year"] = pd.to_datetime(df_cleaned['period'], errors='coerce').dt.year.astype(int)
            df_cleaned = df_cleaned[df_cleaned["year"].between(2014, 2024)]
            
            df_cleaned["iso"] = fetched_df.get("iso", "UNKNOWN") 
            df_cleaned.loc[df_cleaned["series_code"].str.contains("GHA|GH", na=False), "iso"] = "GHA"
            df_cleaned.loc[df_cleaned["series_code"].str.contains("NGA|NG", na=False), "iso"] = "NGA"
            df_cleaned.loc[df_cleaned["series_code"].str.contains("CHN|CN", na=False), "iso"] = "CHN"

            # China 2023 HFCE is intentionally retained as an unresolved blank.
            chn_hfce_mask = df_cleaned["series_code"].eq("A-NE.CON.PRVT.CD-CHN")
            df_cleaned.loc[chn_hfce_mask, "is_imputed"] = False
            
            invalid_rows = (
                df_cleaned["series_code"].isna() | df_cleaned["type"].eq("unknown") | df_cleaned["iso"].eq("UNKNOWN")
            )

            if invalid_rows.any():
                bad_rows = df_cleaned.loc[
                    invalid_rows,
                    ["period", "value", "series_code", "type", "iso"]
                ]
                raise ValueError(
                    f"Invalid macro-series mapping. Refusing to write unknown rows:\n{bad_rows}"
                )

            self.df = df_cleaned
            self.is_from_fallback = False
            print(f"-> Successfully synchronized series from WB, IMF, and HCFE.")
            self.standardise_columns()
            self.clean_data()
            return self.df
        except Exception as e:
            # pull from existing PGSQL database from previous runs if API fails
            try:
                with self.engine.connect() as conn:
                    self.df = pd.read_sql_table(
                        self.name, 
                        con=conn, 
                        schema='Trade Intelligence')
                    if not self.df.empty:
                        print("Warning: API fetch failed. Using existing database data.")
                        self.is_from_fallback = True
                        return self.df
                    else:
                        raise Exception("No existing data available in the database.")
            except Exception as db_e:
                print(f"Database fetch failed: {db_e}")
                raise Exception(f"Critical pipeline error: {e}")
        
    def clean_data(self):
        print("\n--- Data Audit ft. First 10 rows ---")
        print(f"Initial Dimensions: {self.df.shape}")
        print(self.df.head())
        print(self.df.isnull().sum().reset_index(name = 'Missing Values Counted')) # extend a little
        
        print("\n--- Data Types ---")
        print(self.df.dtypes)
        print(self.df.info())
        # Add this right after fetching DB Nomics data:
        print("DB Nomics Unique Data Types:", self.df['type'].unique())
        
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
    
    def connect_database(self, db_path = None): 
        if self.df is None or self.df.empty:
            print("No data to push.")
            return
        
        if getattr(self, 'is_from_fallback', False):
            print(f"Skipping DB-write for '{self.name}' (loaded from fallback)")
            return
        
        try:
            with self.engine.begin() as conn:
                self.df.to_sql(
                    name = self.name, 
                    con = conn, 
                    schema='Trade Intelligence', 
                    if_exists="replace", 
                    index=False
                )
            print(f"Success: Table '{self.name}' written to database.")
        except Exception as e:
            print(f"CRITICAL ERROR during database load: {e}")
        
    
 
    def json_dc(self): 
        return {
            "api_settings": {
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
