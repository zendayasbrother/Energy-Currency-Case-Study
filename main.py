import os
from datacleanse import DataCleaner, Fetcher
from engine import DataEngine
from dotenv import load_dotenv

load_dotenv()

def trilateral_analysis():
    print("Initializing API fetch for Trilateral Analysis...")
    
    countries = "288, 566, 156"
    api_url = os.environ.get('UNCOM_URL')
    api_key = os.environ.get('UNCOM_KEY')
    db_path = os.environ.get('DB_PATH')
    
    print(f"DEBUG: URL found: {api_url is not None}")
    print(f"DEBUG: KEY found: {api_key is not None}")
    
    if api_url is None or api_key is None:
        print("CRITICAL ERROR: .env file isnt set properly")
        exit() # Stop execution
        
    cleaner = DataCleaner(api_url, api_key, countries, db_path)
    fetch = Fetcher(db_path)
    
    # Engine orchestration
    engine = DataEngine(cleaner_ins = None)
    engine.run_analysis() # later dev
    
def run_swat(): 
    trilateral_analysis() # run UI, in this case -- run terminal interface for the website demo

if __name__ == "__main__":
    run_swat()
    
    # 1. PRE-CLEANING RAW DATASET PREVIEW
    # 2. RUN CLEANING PROCESS
    # 3. POST-CLEANING PROCESSED DATASET PREVIEW
    # FORMAT and FINAL REPORT
   