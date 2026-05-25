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
    api_url = os.environ.get('UNCOM_URL') # get API
    cleaner = DataCleaner(api_url)
    # 1. PRE-CLEANING RAW DATASET PREVIEW
    # 2. RUN CLEANING PROCESS
    # 3. POST-CLEANING PROCESSED DATASET PREVIEW
    # FORMAT and FINAL REPORT
   