# test.py
import pytest
import pandas as pd
import os
from unittest.mock import MagicMock
from datacleanse import DataCleaner, Fetcher
from engine import DataEngin

@pytest.fixture
def mock_cleaner():
    cleaner = DataCleaner()
    cleaner.fetch_all = MagicMock(return_value=pd.DataFrame({'a': [1, None]}))
    return cleaner # unsure about mock since i wanna test with the official data, yeah

# Unit Testing
def test_cleaner_removes_nans(mock_cleaner):
    raw_df = pd.DataFrame({'trade': [100, None, 300]})
    processed = mock_cleaner.apply_cleaning_rules(raw_df)
    
    assert processed['trade'].isnull().sum() == 0
    assert len(processed) == 2

# Engine Calcs here