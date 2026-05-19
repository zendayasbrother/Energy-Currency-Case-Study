import pandas as pd
import numpy as np
import wbgapi as wb
from sklearn.linear_model import LinearRegression 
from datacleanse import DataCleaner
from engine import DataEngine

if __name__ == "__main__":
    print("Initializing API fetch for Trilateral Analysis...")
    indicators = {'EG.ELC.ACCS.ZS': 'electricity_access', 'NY.GDP.MKTP.CD': 'gdp'}
    api_raw = wb.data.DataFrame(indicators.keys(), ['NGA', 'GHA'], time=range(2010, 2026))
    
    api_df = api_raw.reset_index().melt(id_vars=['economy', 'series'], var_name='year', value_name='value')
    api_df = api_df.pivot(index=['economy', 'year'], columns='series', values='value').reset_index()
    api_df = api_df.rename(columns=indicators)
    
    # 1. PRE-CLEANING RAW DATASET PREVIEW
    print("\n--- FULL TRILATERAL DATASET (PRE-CLEANING: 2010-2025) ---")
    raw_sorted = api_df.sort_values(['economy', 'year'])
    for eco in raw_sorted['economy'].unique():
        print(f"\n{'='*20} ECONOMY: {eco} (RAW) {'='*20}")
        print(raw_sorted[raw_sorted['economy'] == eco].to_string(index=False))
        print(f"{'-'*60}")

    # 2. RUN CLEANING PROCESS
    cleaner = DataCleaner(api_df)
    cleaned_df = cleaner.clean_data()

    # 3. POST-CLEANING PROCESSED DATASET PREVIEW
    print("\n--- FULL TRILATERAL DATASET (POST-CLEANING: 2010-2025) ---")
    full_report = cleaned_df.sort_values(['economy', 'year'])
    
    # Helper for 4-digit total constraint (e.g. 32.19, 366.9, 252.2)
    gdp_fmt = cleaner.formatter()

    for eco in full_report['economy'].unique():
        print(f"\n{'='*20} ECONOMY: {eco} (PROCESSED) {'='*20}")
        print(full_report[full_report['economy'] == eco].to_string(
            index=False, 
            formatters={
                'electricity_access': '{:.2f}'.format,
                'gdp': gdp_fmt
            }
        ))
        print(f"{'-'*60}")

    cleaner.gen_json()
    print("\n--- SUCCESS: DATA SERIALIZED TO JSON ---")