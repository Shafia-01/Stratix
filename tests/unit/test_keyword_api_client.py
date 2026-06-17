import pytest
import requests
from src.keyword_api_client import KeywordAPIClient
from src.data_quality import DataSource

@pytest.mark.unit
def test_keyword_client_constructor_modes(monkeypatch, mocker):
    # Patch module level variables to ensure clean constructor state
    monkeypatch.setattr("src.keyword_api_client.FORCE_SANDBOX", False)
    monkeypatch.setattr("src.keyword_api_client.DEMO_MODE", False)
    monkeypatch.setattr("src.keyword_api_client.PRESERVE_CREDITS", False)
    monkeypatch.setattr("src.keyword_api_client.DATAFORSEO_USERNAME", None)
    monkeypatch.setattr("src.keyword_api_client.DATAFORSEO_PASSWORD", None)

    # 1. Missing credentials
    mock_check_balance = mocker.patch.object(KeywordAPIClient, "_check_balance")
    client = KeywordAPIClient()
    mock_check_balance.assert_not_called()
    assert client.using_sandbox is False

    # Restore/set creds for next cases
    monkeypatch.setattr("src.keyword_api_client.DATAFORSEO_USERNAME", "some_user")
    monkeypatch.setattr("src.keyword_api_client.DATAFORSEO_PASSWORD", "some_pass")

    # Mock _check_balance to avoid requests during construction
    mocker.patch.object(KeywordAPIClient, "_check_balance", return_value=10.0)

    # 2. Force sandbox
    monkeypatch.setattr("src.keyword_api_client.FORCE_SANDBOX", True)
    client_sandbox = KeywordAPIClient()
    assert client_sandbox.using_sandbox is True
    assert "sandbox" in client_sandbox.base_url

    # 3. Demo mode
    monkeypatch.setattr("src.keyword_api_client.FORCE_SANDBOX", False)
    monkeypatch.setattr("src.keyword_api_client.DEMO_MODE", True)
    client_demo = KeywordAPIClient()
    assert client_demo.using_sandbox is True
    assert "sandbox" in client_demo.base_url


@pytest.mark.unit
def test_is_account_limited_error():
    client = KeywordAPIClient()

    # HTTP Status Code classifications
    assert client._is_account_limited_error(402, {}) == (True, "balance_zero")
    assert client._is_account_limited_error(429, {}) == (True, "rate_limited")
    assert client._is_account_limited_error(401, {}) == (True, "unauthorized")

    # DataForSEO status code variants
    assert client._is_account_limited_error(200, {"status_code": 40200}) == (True, "balance_zero")
    assert client._is_account_limited_error(200, {"status_code": 42900}) == (True, "rate_limited")
    assert client._is_account_limited_error(200, {"status_code": 40100}) == (True, "unauthorized")
    assert client._is_account_limited_error(200, {"status_code": 40001}) == (False, None)


@pytest.mark.unit
def test_get_keyword_suggestions_missing_credentials_fallback(monkeypatch, mocker, mock_gemini):
    monkeypatch.setattr("src.keyword_api_client.DATAFORSEO_USERNAME", None)
    monkeypatch.setattr("src.keyword_api_client.DATAFORSEO_PASSWORD", None)
    monkeypatch.setattr("src.keyword_api_client.FORCE_SANDBOX", False)
    monkeypatch.setattr("src.keyword_api_client.DEMO_MODE", False)

    client = KeywordAPIClient()
    mock_post = mocker.patch.object(requests.Session, "post")

    # Should fall back to Gemini without making HTTP calls to DataForSEO
    res = client.get_keyword_suggestions("coffee", max_keywords=2)
    mock_post.assert_not_called()
    assert len(res) == 2
    assert res[0]["data_source"] == DataSource.UNAVAILABLE.value


@pytest.mark.unit
def test_get_keyword_suggestions_relevance_filter(monkeypatch, mocker, mock_gemini):
    # Setup client with credentials
    monkeypatch.setattr("src.keyword_api_client.DATAFORSEO_USERNAME", "test_user")
    monkeypatch.setattr("src.keyword_api_client.DATAFORSEO_PASSWORD", "test_pass")
    monkeypatch.setattr("src.keyword_api_client.FORCE_SANDBOX", False)
    monkeypatch.setattr("src.keyword_api_client.DEMO_MODE", False)
    mocker.patch.object(KeywordAPIClient, "_check_balance", return_value=100.0)

    client = KeywordAPIClient()

    # Case A: Suggestions are completely irrelevant (shared words < 30%)
    mocker.patch.object(client, "_get_dataforseo_suggestions", return_value=(["car guide", "house insurance"], None))
    # It should fallback to Gemini (which returns "organic coffee guides", "best organic coffee beans")
    res_fallback = client.get_keyword_suggestions("organic coffee", max_keywords=2)
    assert any("coffee" in item["keyword"] for item in res_fallback)


@pytest.mark.unit
def test_sort_keywords_by_opportunity():
    client = KeywordAPIClient()

    metrics = [
        {"keyword": "low opp", "search_volume": 100, "competition": 0.9},
        {"keyword": "high opp", "search_volume": 80000, "competition": 0.1}
    ]
    # Opportunity score formula: 0.7 * normalized_volume + 0.3 * (1 - competition)
    # normalized_volume = min(volume / 100000, 1.0)
    # low opp: volume=100 -> 0.001. comp=0.9 -> 0.1. Score = 0.7 * 0.001 + 0.3 * 0.1 = 0.0007 + 0.03 = 0.031
    # high opp: volume=80000 -> 0.8. comp=0.1 -> 0.9. Score = 0.7 * 0.8 + 0.3 * 0.9 = 0.56 + 0.27 = 0.83

    sorted_kws = client._sort_keywords_by_opportunity(metrics, max_keywords=2)
    assert sorted_kws[0]["keyword"] == "high opp"
    assert sorted_kws[0]["opportunity_score"] > sorted_kws[1]["opportunity_score"]


@pytest.mark.unit
def test_fallback_to_gemini_padding(mock_gemini):
    client = KeywordAPIClient()
    # Mock generate_keywords to return only 1 keyword
    import src.keyword_api_client
    src.keyword_api_client.generate_keywords = lambda seed, max_kw: ["coffee bean"]

    # Request 5 keywords. The client should pad with deterministic variations
    res = client._fallback_to_gemini("coffee", max_keywords=5)
    assert len(res) == 5
    assert res[0]["keyword"] == "coffee bean"
    assert res[1]["keyword"] == "coffee guide"


@pytest.mark.unit
def test_get_keyword_metrics_single_keyword(monkeypatch, mocker):
    monkeypatch.setattr("src.keyword_api_client.DATAFORSEO_USERNAME", "test")
    monkeypatch.setattr("src.keyword_api_client.DATAFORSEO_PASSWORD", "test")
    monkeypatch.setattr("src.keyword_api_client.FORCE_SANDBOX", False)
    monkeypatch.setattr("src.keyword_api_client.DEMO_MODE", False)
    mocker.patch.object(KeywordAPIClient, "_check_balance", return_value=100.0)

    client = KeywordAPIClient()

    # Success path
    mocker.patch.object(client, "_get_keyword_metrics_batch", return_value=([
        {"keyword": "coffee", "search_volume": 500, "competition": 0.5, "cpc": 1.0}
    ], None))

    metrics = client.get_keyword_metrics("coffee")
    assert metrics["volume"] == 500
    assert metrics["data_source"] == DataSource.LIVE.value

    # Failure path
    mocker.patch.object(client, "_get_keyword_metrics_batch", return_value=([], ("error", {})))
    metrics_fail = client.get_keyword_metrics("coffee")
    assert metrics_fail["data_source"] == DataSource.UNAVAILABLE.value
