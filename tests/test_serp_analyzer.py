import pytest
from unittest.mock import patch
from src.serp_analyzer import analyze_serp_opportunities, get_serp_data
from src.exceptions import KeylyticsAPIError

@patch("src.serp_analyzer.SERPAPI_KEY", None)
def test_get_serp_data_no_key():
    with pytest.raises(KeylyticsAPIError, match="SERPAPI_KEY not found"):
        get_serp_data("test keyword")

@patch("src.serp_analyzer.SERPAPI_KEY", "dummy_key")
@patch("requests.get")
def test_get_serp_data_api_error(mock_get):
    mock_get.return_value.status_code = 500
    mock_get.return_value.text = "Internal Server Error"
    
    with pytest.raises(KeylyticsAPIError, match="SERP API returned status 500"):
        get_serp_data("test keyword")

@patch("src.serp_analyzer.SERPAPI_KEY", "dummy_key")
@patch("requests.get")
def test_analyze_serp_opportunities_handles_exception(mock_get):
    mock_get.side_effect = Exception("Connection error")
    
    result = analyze_serp_opportunities("test keyword")
    assert "error" in result
    assert "Failed to fetch SERP data" in result["error"]
