import pytest
from src.agent import process_keyword
from src.data_quality import DataSource

def test_process_keyword_no_trend(monkeypatch):
    # Mock get_trend_score to return None
    monkeypatch.setattr("src.agent.get_trend_score", lambda kw: None)
    # Mock get_competitor_data to return empty list
    monkeypatch.setattr("src.agent.get_competitor_data", lambda kw: [])
    # Mock classify_intent to return informational
    monkeypatch.setattr("src.agent.classify_intent", lambda kw: "informational")
    
    kw_item = {
        "keyword": "test kw",
        "volume": 1000,
        "competition": 0.5,
        "cpc": 1.0,
        "data_source": DataSource.LIVE.value
    }
    
    result = process_keyword(kw_item, "seed")
    
    assert result is not None
    assert result["trend"] is None
    assert result["trend_data_source"] == DataSource.UNAVAILABLE.value
    # Base score = (1000 * 0.5 + 1.0 * 100 * 0.3 + (1 - 0.5) * 100 * 0.2) / 100
    # = (500 + 30 + 10) / 100 = 5.4
    # final_score = round(0.8 * score + 0.2 * score) = score = 5.4
    assert result["score"] == 5.4
