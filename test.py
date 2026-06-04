# test.py
import pytest
import pandas as pd
from unittest.mock import MagicMock
from datacleanse import DataCleaner, Fetch

# 1. FIXTURES: Define your "Input" state
@pytest.fixture
def mock_cleaner():
    # We return a cleaner object but with a mocked API layer
    cleaner = DataCleaner(api_url="http://mock.url", api_key="test_key")
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