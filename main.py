import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
from sklearn.linear_model import LinearRegression 
from datacleanse import DataCleaner
from engine import DataEngine

if __name__ == "__main__":
    print("Initializing API fetch for Trilateral Analysis...")
    load_dotenv()
    country_codes = "288, 566, 156"
    api_url = os.environ.get('UNCOM_URL') # get API creds
    api_key = os.environ.get('UNCOM_KEY')
    
    if api_url is None or api_key is None:
        print("CRITICAL ERROR: .env file isnt set properly")
        exit() # Stop execution
        
    cleaner = DataCleaner(api_url, api_key, country_codes)
    # 1. PRE-CLEANING RAW DATASET PREVIEW
    # 2. RUN CLEANING PROCESS
    # 3. POST-CLEANING PROCESSED DATASET PREVIEW
    # FORMAT and FINAL REPORT
   