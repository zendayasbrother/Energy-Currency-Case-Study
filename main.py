import os
import sys
from pathlib import Path
from datacleanse import DataCleaner, Fetcher
from dotenv import load_dotenv
from engine import DataEngine
from models import ECModels

base_path = Path(__file__).resolve().parent
env_path = base_path / ".env"
load_dotenv(dotenv_path=env_path)


def trilateral_analysis():
    print("Initializing API fetch for Trilateral Analysis...") # functions per file - datacleanse.py
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
    fetcher = Fetcher(db_path=db_path)
    engine = DataEngine(cleaner=cleaner, fetcher=fetcher)

    try:
        # Engine Orchestration
        engine.sync_matrix(countries)
        engine.run_stats()
        engine.run_corr()
        return engine, cleaner, fetcher
    except Exception as e:
        print(f"Analytical Engine Pipeline failed: {e}")
        return False

def model_analysis(df, engine):
    models = ECModels(df)
    
    gap_results = engine.energy_equity_gap()

    if gap_results is not None:
        # Process symbolic regression / equity gap results
        print("Energy Equity Gap Results:", gap_results)
    else:
        print("Notice: Proceeding with remaining linear regression models without Equity Gap analysis.")
        
    # Execute the linear regression model to generate the 'frame' data
    frame = models.run_linear_regression()
    return engine, frame

def run_swat():
    
    print("\nHello, and welcome to SWAT: a computational demonstration of the trilateral relationship of China, Nigeria, and Ghana.")
    
    result = trilateral_analysis()
    if not result:
        print("\nSWAT Fatal: Application dashboard execution halted due to engine synchronization failures.")
        return

    # Unpack the tuple returned by trilateral_analysis()
    engine, cleaner, fetcher = result

    df = engine.df
    engine, frame = model_analysis(df, engine)

    if not frame: 
        print("\nSWAT Fatal: Application dashboard execution halted due to model analysis failures.")
        return
    else:
        print("\nSWAT Success: Model analysis completed.")
        print(f"Target: {frame['target']} | Predictor: {frame['predictor']} | R-Squared: {frame['r_squared']}")
        
if __name__ == "__main__":
    try:
        run_swat()
    except Exception as e:
        print(f"\nUnhandled Error: {e}")
    finally:
        print("\n" + "=" * 50)
        input("Press [ENTER] to close debugger...")