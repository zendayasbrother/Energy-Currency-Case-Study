# test.py
import pytest
import pandas as pd
import numpy as np
import os
from unittest.mock import MagicMock
from unittest.mock import Mock
from datacleanse import DataCleaner, Fetcher
from engine import DataEngine

@pytest.fixture
def mock_env_variables():
    # Provides fake configuration strings for class initializations
    return {
        "db_path": "sqlite:///:memory:",  
        "api_url": "https://api.comtrade.un.org/v1",
        "api_key": "fake_key_123",
        "countries": [288, 566, 156]
    }

@pytest.fixture
def sample_uncom_df():
    # Generates mock UN Comtrade data with pre-lowercased headers.
    return pd.DataFrame({
        'reportercode': [156, 566, 288],
        'refyear': [2022, 2022, 2022],
        'primaryvalue': [500000.0, np.nan, 120000.0],
        'custom_header_space': [1, 2, 3]
    })

@pytest.fixture
def sample_dbnomics_df():
    # Generates mock DBNomics data matching intermediate engine structure.
    return pd.DataFrame({
        'period': ['2022', '2022', '2022', '2022'],
        'value': [5.4, 14.2, 4.15, 195.5],
        'series_code': ['WB.WDI.FP.CPI.TOTL.ZG.CHN', 'WB.WDI.FP.CPI.TOTL.ZG.NGA', 'IMF.IFS.ENDE_XDC_USD_RATE.GH', 'IMF.IFS.ENDE_XDC_USD_RATE.NG'],
        'year': [2022, 2022, 2022, 2022],
        'type': ['inflation', 'inflation', 'exchange_rate', 'exchange_rate'] # Critical for pivot table operation
    })


def test_column_standardisation(mock_env_variables):
    # Verifies that column strings are formatted consistently across providers
    cleaner = DataCleaner(db_path=mock_env_variables["db_path"])
    cleaner.df = pd.DataFrame(columns=['Ref-Year', 'Trade Value (USD)', 'Gross–Wgt'])
    
    cleaner.standardise_columns()
    
    expected_cols = ['ref_year', 'trade_value_(usd)', 'gross_wgt']
    assert list(cleaner.df.columns) == expected_cols


def test_nans(mock_env_variables, sample_uncom_df):
    # Ensures numeric NaNs turn to zero and specified columns are safely dropped.
    cleaner = DataCleaner(db_path=mock_env_variables["db_path"])
    cleaner.df = sample_uncom_df
    
    cleaner.standardise_columns() # Essential prefix to lowercase columns
    cleaner.clean_data()
    
    # Assert missing numeric properties are filled with 0
    assert cleaner.df['primaryvalue'].isnull().sum() == 0
    assert cleaner.df['primaryvalue'].iloc[1] == 0
    
    # Assert specific metadata items are excluded
    assert 'refyear' not in cleaner.df.columns