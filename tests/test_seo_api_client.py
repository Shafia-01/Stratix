import pytest
import requests
from src.seo_api_client import get_keyword_metrics
from src.data_quality import DataSource

def test_get_keyword_metrics_failure(monkeypatch):
    def mock_get(*args, **kwargs):
        raise requests.exceptions.RequestException("API error")
    
    monkeypatch.setattr(requests, "get", mock_get)
    # Bypass check_cache so it runs the SerpApi fetch
    monkeypatch.setattr("src.seo_api_client.check_cache", lambda kw: None)
    
    result = get_keyword_metrics("failing_keyword")
    
    assert result["volume"] == 0
    assert result["competition"] is None
    assert result["cpc"] is None
    assert result["data_source"] == DataSource.UNAVAILABLE.value
