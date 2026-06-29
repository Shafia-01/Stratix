import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import requests
import src.db_client
import src.seo_api_client
import src.gemini_client

@pytest.fixture(scope="session", autouse=True)
def mock_env_vars():
    """Inject dummy credentials for all external services to avoid live calls or missing key errors."""
    os.environ["GEMINI_API_KEY"] = "mock_gemini_api_key"
    os.environ["SERPAPI_KEY"] = "mock_serpapi_key"
    os.environ["DATAFORSEO_USERNAME"] = "mock_username"
    os.environ["DATAFORSEO_PASSWORD"] = "mock_password"
    os.environ["DATAFORSEO_DEMO_MODE"] = "false"
    os.environ["DATAFORSEO_FORCE_SANDBOX"] = "false"
    os.environ["STRATIX_API_KEY"] = ""
    os.environ["STRATIX_AI_API_KEY"] = ""
    os.environ["KEYLYTICS_API_KEY"] = ""  # disable auth in tests
    os.environ["STRATIX_ENV"] = "development"
    os.environ["KEYLYTICS_ENV"] = "development"
    os.environ["STRATIX_LOG_LEVEL"] = "INFO"
    os.environ["KEYLYTICS_LOG_LEVEL"] = "INFO"

@pytest.fixture(autouse=True)
def tmp_db_path(tmp_path, monkeypatch):
    """Creates a temporary SQLite database per test."""
    db_file = tmp_path / "test_keylytics.db"
    monkeypatch.setenv("STRATIX_DB_PATH", str(db_file))
    monkeypatch.setenv("KEYLYTICS_DB_PATH", str(db_file))

    # Reset engine and path singletons in db_client
    src.db_client._engine = None
    src.db_client.DB_PATH = str(db_file)

    yield db_file

    # Cleanup after test
    src.db_client._engine = None
    if db_file.exists():
        try:
            os.remove(db_file)
        except Exception:
            pass

@pytest.fixture
def mock_http(monkeypatch):
    """Fixture to mock requests.get, requests.post, requests.Session.get, requests.Session.post."""
    class MockResponse:
        def __init__(self, json_data, status_code=200, text=""):
            self._json = json_data
            self.status_code = status_code
            self.text = text

        def json(self):
            return self._json

    def mock_get(url, *args, **kwargs):
        if "serpapi.com" in url:
            return MockResponse({
                "search_information": {"total_results": 2500000},
                "organic_results": [
                    {"link": "https://competitor1.com/page", "title": "Competitor 1 Title"},
                    {"link": "https://competitor2.com/page", "title": "Competitor 2 Title"}
                ],
                "people_also_ask": [
                    {"question": "How to brew coffee?", "snippet": "Brew coffee by mixing coffee grounds and hot water."}
                ]
            })
        return MockResponse({})

    def mock_post(url, *args, **kwargs):
        if "user" in url:
            return MockResponse({"balance": 100.0})
        elif "keywords_for_keywords" in url or "keyword_ideas" in url:
            return MockResponse({
                "status_code": 20000,
                "tasks": [{
                    "status_code": 20000,
                    "result": [{
                        "items": [
                            {"keyword": "organic coffee guides"},
                            {"keyword": "best organic coffee beans"}
                        ]
                    }]
                }]
            })
        elif "search_volume" in url:
            return MockResponse({
                "status_code": 20000,
                "tasks": [{
                    "status_code": 20000,
                    "result": [[
                        {
                            "keyword": "organic coffee guides",
                            "search_volume": 1500,
                            "competition": 0.45,
                            "cpc": 1.25
                        },
                        {
                            "keyword": "best organic coffee beans",
                            "search_volume": 800,
                            "competition": 0.8,
                            "cpc": 2.1
                        }
                    ]]
                }]
            })
        return MockResponse({})

    monkeypatch.setattr(requests, "get", mock_get)
    monkeypatch.setattr(requests, "post", mock_post)
    monkeypatch.setattr(requests.Session, "get", mock_get)
    monkeypatch.setattr(requests.Session, "post", mock_post)

@pytest.fixture
def mock_gemini(monkeypatch):
    """Fixture to mock safe_gemini_call."""
    def mock_safe_call(prompt, *args, **kwargs):
        prompt_lower = prompt.lower()
        if "search intent" in prompt_lower or "intent" in prompt_lower:
            return "Commercial"
        elif "group them into 3-8 semantic clusters" in prompt_lower:
            return """
            {
                "clusters": [
                    {
                        "cluster_name": "Organic Coffee Tips",
                        "description": "Guides and tutorials on organic coffee",
                        "keywords": ["organic coffee guides"],
                        "primary_intent": "informational",
                        "industry_focus": "food"
                    }
                ]
            }
            """
        elif "semantic variations" in prompt_lower or "generate 20 semantic variations" in prompt_lower:
            return "organic coffee guides\nbest organic coffee beans\norganic coffee benefits"
        elif "people also ask question" in prompt_lower:
            return "Guide to Brewing Organic Coffee"
        elif "identify 10 keywords" in prompt_lower or "missing keywords" in prompt_lower:
            return """[
                {"keyword": "overlooked organic coffee", "opportunity_type": "semantic_gap", "difficulty_estimate": "easy"}
            ]"""
        # Default response for keyword generation
        return "organic coffee guides\nbest organic coffee beans"

    monkeypatch.setattr(src.gemini_client, "safe_gemini_call", mock_safe_call)
