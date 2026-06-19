# test.py
import pytest
import pandas as pd
import numpy as np
import os
from unittest.mock import MagicMock
from unittest.mock import Mock
from mock import patch
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


@patch('datacleanse.requests.get')
def test_uncom_api_fetch_rate_limiting(mock_get, mock_env_variables):
    # Simulates handling HTTP status 429 backoff gracefully without raising crashes.
    cleaner = DataCleaner(
        db_path=mock_env_variables["db_path"],
        api_url=mock_env_variables["api_url"],
        api_key=mock_env_variables["api_key"]
    )
    
    # Mock a response object representing a rate limit hit
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_get.return_value = mock_response

    # Temporarily patch time.sleep so the test executes instantly
    with patch('time.sleep', return_value=None):
        with pytest.raises(Exception, match="No data could be retrieved."):
            cleaner.fetch_api(countries=[156])


def test_engine_matrix_sync(mock_env_variables, sample_uncom_df, sample_dbnomics_df):
    # Validates data merging and structural alignment inside the engine.
    # Instantiating base classes
    cleaner = DataCleaner(db_path=mock_env_variables["db_path"])
    fetch = Fetcher(db_path=mock_env_variables["db_path"])
    
    # Isolate Engine from executing actual outward API commands by forcing mock returns
    cleaner.fetch_api = MagicMock(return_value=sample_uncom_df)
    fetch.fetch_all = MagicMock(return_value=sample_dbnomics_df)
    
    # Initialize Engine pipeline execution
    engine = DataEngine(cleaner, fetch, countries=mock_env_variables["countries"])
    
    # Check if horizontal merge aligned indices properly
    assert not engine.df.empty
    assert 'country_iso' in engine.df.columns
    assert 'exchange_rate' in engine.df.columns or 'inflation' in engine.df.columns
    
    # Check ISO assignments
    china_row = engine.df[engine.df['country_iso'] == 'CHN']
    assert not china_row.empty


def test_engine_descriptives(mock_env_variables):
    # Verifies descriptive matrices generate custom statistical markers correctly.
    cleaner = MagicMock()
    fetch = MagicMock()
    
    # Constructing a manual, clean dataframe directly inside engine bypass
    engine = DataEngine.__new__(DataEngine) 
    engine.df = pd.DataFrame({
        'trade_val': [10, 20, 30, 40, 50],
        'exchange_rate': [1.5, 2.0, 2.5, 3.0, 3.5]
    })
    
    stats_summary, corr_matrix = engine.run_analysis()
    
    assert 'median' in stats_summary.index
    assert 'var' in stats_summary.index
    assert corr_matrix.loc['trade_val', 'exchange_rate'] == pytest.approx(1.0)