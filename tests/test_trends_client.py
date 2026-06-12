import pytest
import pandas as pd
from src.trends_client import get_trend_history, get_trend_score
from pytrends.request import TrendReq

def test_get_trend_history_success(monkeypatch):
    # Mock _fetch_pytrends_dataframe instead of the whole request to be clean
    dates = pd.date_range(start="2025-01-01", end="2025-03-01", freq="W")
    df = pd.DataFrame({"test kw": [40, 42, 44, 46, 48, 50, 52, 54]}, index=dates)
    
    monkeypatch.setattr("src.trends_client._fetch_pytrends_dataframe", lambda kw: df)
    
    history = get_trend_history("test kw")
    
    assert history is not None
    assert len(history) > 0
    assert "date" in history[0]
    assert "score" in history[0]
    assert isinstance(history[0]["score"], int)

def test_get_trend_history_failure(monkeypatch):
    # Mock _fetch_pytrends_dataframe to return None
    monkeypatch.setattr("src.trends_client._fetch_pytrends_dataframe", lambda kw: None)
    
    history = get_trend_history("test kw")
    
    assert history is None
