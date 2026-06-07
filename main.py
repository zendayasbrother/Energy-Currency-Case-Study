import os
from datacleanse import DataCleaner, Fetcher
from engine import DataEngine
from pathlib import Path
from dotenv import load_dotenv

base_path = Path(__file__).resolve().parent
env_path = base_path / '.env'

load_dotenv(dotenv_path=env_path)

def trilateral_analysis():
    print("Initializing API fetch for Trilateral Analysis...")
    
    countries = ["288", "566", "156"]       
    api_url = os.environ.get('UNCOM_URL')
    api_key = os.environ.get('UNCOM_KEY')
    db_path = os.environ.get('DB_PATH')
    countries = [288, 566, 156]
    
    print(f"DEBUG: URL found: {api_url is not None}")
    print(f"DEBUG: KEY found: {api_key is not None}")
    
    if api_url is None or api_key is None:
        print("CRITICAL ERROR: .env file isnt set properly")
        exit() # Stop execution
        
    cleaner = DataCleaner(api_url, api_key, countries, db_path)
    fetch = Fetcher(db_path)
    try:
        cleaner.fetch_api(countries)
        clean.clean_data()
        cleaner.connect_database(db_path=None) # bilateral trade
        
        fetch.fetch_all()
        fetch.clean_data()
        fetch.connect_database() # monetary
        
        # Engine orchestration 
        engine = DataEngine(cleaner_ins = cleaner)
        engine.run_analysis() # later dev
    except Exception as e:
        print(f"Failed to fetch data or run engine: {e}")
    
def run_swat(): 
    trilateral_analysis() # run UI, in this case -- run terminal interface for the website demo
    print("Hello, and welcome to SWAT: a computational demonstration of the trilateral relationship of China, Nigeria, and Ghana.")

if __name__ == "__main__":
    run_swat()
    
    # 1. PRE-CLEANING RAW DATASET PREVIEW
    # 2. RUN CLEANING PROCESS
    # 3. POST-CLEANING PROCESSED DATASET PREVIEW
    # FORMAT and FINAL REPORT
   