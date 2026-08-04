from unittest.mock import patch
import pandas as pd
from src.trends_client import get_trend_history

def test_get_trend_history_live():
    # Mocking _fetch_pytrends_dataframe to return a valid DataFrame
    df = pd.DataFrame({"test_keyword": [50, 60, 70]}, index=pd.date_range("2025-01-01", periods=3, freq="ME"))
    with patch("src.trends_client._fetch_pytrends_dataframe", return_value=df):
        history, source = get_trend_history("test_keyword")
        assert source == "live"
        assert len(history) == 3
        assert history[0]["score"] == 50

def test_get_trend_history_fallback():
    # Mocking _fetch_pytrends_dataframe to return None (failure)
    with patch("src.trends_client._fetch_pytrends_dataframe", return_value=None):
        history, source = get_trend_history("fallback_keyword")
        assert source == "estimated"
        assert len(history) == 12
        # Ensure all scores are integers between 0 and 100
        for item in history:
            assert isinstance(item["score"], int)
            assert 0 <= item["score"] <= 100
            assert "date" in item
