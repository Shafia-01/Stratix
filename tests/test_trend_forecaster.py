import pytest
from src.trend_forecaster import generate_trend_forecasts, analyze_trend_forecasting

def test_generate_trend_forecasts_determinism():
    trend_analysis = {
        "test keyword": {
            "current_trend": 50,
            "historical_scores": [
                {"month": 1, "score": 45, "date": "2025-01"},
                {"month": 2, "score": 50, "date": "2025-02"},
                {"month": 3, "score": 55, "date": "2025-03"}
            ],
            "metrics": {"slope": 5.0, "r_squared": 1.0, "avg_change": 5.0},
            "direction": "strong_growth",
            "volatility": 4.0,
            "peak_month": 3,
            "growth_rate": 22.2
        }
    }
    
    forecasts1, unavailable1 = generate_trend_forecasts(trend_analysis)
    forecasts2, unavailable2 = generate_trend_forecasts(trend_analysis)
    
    assert forecasts1 == forecasts2
    assert unavailable1 == unavailable2
    assert "test keyword" in forecasts1
    assert len(forecasts1["test keyword"]["forecast_scores"]) == 6
    assert forecasts1["test keyword"]["forecast_scores"][0]["score"] == 55.0  # current_trend 50 + slope 5.0 * 1

def test_generate_trend_forecasts_unavailable():
    trend_analysis = {
        "available keyword": {
            "current_trend": 50,
            "historical_scores": [
                {"month": 1, "score": 45, "date": "2025-01"}
            ],
            "metrics": {"slope": 0, "r_squared": 0, "avg_change": 0},
            "direction": "stable",
            "volatility": 0.0,
            "peak_month": 1,
            "growth_rate": 0.0
        },
        "unavailable keyword": {
            "current_trend": None,
            "historical_scores": [],
            "metrics": {"slope": 0, "r_squared": 0, "avg_change": 0},
            "direction": "stable",
            "volatility": 0.0,
            "peak_month": None,
            "growth_rate": 0.0
        }
    }
    
    forecasts, unavailable = generate_trend_forecasts(trend_analysis)
    
    assert "unavailable keyword" in unavailable
    assert "unavailable keyword" not in forecasts
    assert "available keyword" in forecasts

def test_analyze_trend_forecasting_disclaimer():
    keywords_data = [{"keyword": "dummy", "volume": 100, "competition": 0.5}]
    
    # Mock the API client calls inside analyze_trend_forecasting
    import src.trend_forecaster
    original_get_historical_trends = src.trend_forecaster.get_historical_trends
    src.trend_forecaster.get_historical_trends = lambda k: {
        "dummy": {
            "current_trend": 50,
            "historical_scores": [{"month": 1, "score": 50, "date": "2025-01"}],
            "volume": 100,
            "competition": 0.5
        }
    }
    
    try:
        result = analyze_trend_forecasting(keywords_data)
        assert "disclaimer" in result
        assert len(result["disclaimer"]) > 0
    finally:
        src.trend_forecaster.get_historical_trends = original_get_historical_trends
