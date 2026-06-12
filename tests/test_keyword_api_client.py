import pytest
import requests
from src.keyword_api_client import get_enhanced_keywords
from src.data_quality import DataSource

def test_get_enhanced_keywords_failure(monkeypatch):
    # Mock post to raise exception
    def mock_post(*args, **kwargs):
        raise requests.exceptions.RequestException("Network down")
    
    monkeypatch.setattr(requests.Session, "post", mock_post)
    
    # Mock Gemini call inside fallback to return a fixed list
    monkeypatch.setattr("src.keyword_api_client.generate_keywords", lambda kw, limit: ["fallback kw"])
    
    results = get_enhanced_keywords("test_keyword", max_keywords=5)
    
    # Check that they returned our fallback keywords with zero volume / None competition / unavailable source
    assert len(results) > 0
    for r in results:
        assert r["volume"] == 0
        assert r["competition"] is None
        assert r["cpc"] is None
        assert r["data_source"] == DataSource.UNAVAILABLE.value
        assert "opportunity_score" in r
