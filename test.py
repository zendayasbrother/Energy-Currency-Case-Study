# test.py
import pytest
import pandas as pd
import os
from unittest.mock import MagicMock
from datacleanse import DataCleaner, Fetch
from dotenv import load_dotenv

load_dotenv()

# 1. FIXTURES: Define your "Input" state
@pytest.fixture
def mock_cleaner():
    print("Initializing API fetch for Trilateral Analysis...")
    load_dotenv()
    country_codes = "288, 566, 156"
    api_url = os.environ.get('UNCOM_URL') # get API creds
    api_key = os.environ.get('UNCOM_KEY')
    
    print(f"DEBUG: URL found: {api_url is not None}")
    print(f"DEBUG: KEY found: {api_key is not None}")
    
    if api_url is None or api_key is None:
        print("CRITICAL ERROR: .env file isnt set properly")
        exit() # Stop execution
        
    cleaner = DataCleaner(api_url, api_key, country_codes)
    cleaner.clean_data()
    # We return a cleaner object but with a mocked API layer
    cleaner = DataCleaner(api_url, api_key)
    cleaner.fetch_all = MagicMock(return_value=pd.DataFrame({'a': [1, None]}))
    return cleaner

# 2. UNIT TESTS: Assert logic, not network connectivity
def test_cleaner_removes_nans(mock_cleaner):
    raw_df = pd.DataFrame({'trade': [100, None, 300]})
    processed = mock_cleaner.apply_cleaning_rules(raw_df)
    
    assert processed['trade'].isnull().sum() == 0
    assert len(processed) == 2

# 3. INTEGRATION TESTS: Does the engine handle the dataframe?
def test_engine_calculation():
    from engine import DataEngine
    engine = DataEngine()
    df = pd.DataFrame({'value': [10, 20, 30]})
    
    # Asserting the Gini coefficient or stats calculation
    result = engine.calculate_stats(df)
    assert 'mean' in result
    assert result['mean'] == 20