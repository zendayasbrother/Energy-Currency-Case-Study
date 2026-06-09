import os
from pathlib import Path
from datacleanse import DataCleaner, Fetcher
from dotenv import load_dotenv
from engine import DataEngine

base_path = Path(__file__).resolve().parent
env_path = base_path / ".env"
load_dotenv(dotenv_path=env_path)


def trilateral_analysis():
    print("Initializing API fetch for Trilateral Analysis...")

    api_url = os.environ.get("UNCOM_URL")
    api_key = os.environ.get("UNCOM_KEY")
    db_path = os.environ.get("DB_PATH")
    countries = [288, 566, 156]

    print(f"DEBUG: URL found: {api_url is not None}")
    print(f"DEBUG: KEY found: {api_key is not None}")

    if api_url is None or api_key is None or db_path is None:
        print("CRITICAL ERROR: .env file elements missing")
        return

    cleaner = DataCleaner(db_path=db_path, api_url=api_url, api_key=api_key, countries=countries)
    fetch = Fetcher(db_path=db_path)
    
    try:
        cleaner.fetch_api(countries)
        cleaner.clean_data()
        cleaner.connect_database()
    except Exception as e:
        print(f"UN Comtrade Pipeline failed: {e}")

    try:
        fetch.fetch_all()
        fetch.clean_data()
        fetch.connect_database()
    except Exception as e:
        print(f"DBNomics Pipeline failed: {e}")

    try:
        # Engine Orchestration
        engine_instance = DataEngine(cleaner_ins=cleaner)
        engine_instance.run_analysis()
    except Exception as e:
        print(f"Analytical Engine Pipeline failed: {e}")


def run_swat():
    trilateral_analysis()
    print("\nHello, and welcome to SWAT: a computational demonstration of the trilateral relationship of China, Nigeria, and Ghana.")


if __name__ == "__main__":
    run_swat()
     
    # 1. PRE-CLEANING RAW DATASET PREVIEW
    # 2. RUN CLEANING PROCESS
    # 3. POST-CLEANING PROCESSED DATASET PREVIEW
    # FORMAT and FINAL REPORT
   