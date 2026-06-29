"""
FastAPI route integration tests using TestClient.
All external tool calls are mocked so tests run offline with no API keys needed.
Covers: health, keywords (research + history), and all 5 intelligence endpoints.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from api.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------
class TestHealthRoute:
    def test_health_returns_200(self, client):
        with (
            patch("api.routes.health.connect_db"),
            patch("api.routes.health.verify_database_schema", return_value=True),
            patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        ):
            resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_response_shape(self, client):
        with (
            patch("api.routes.health.connect_db"),
            patch("api.routes.health.verify_database_schema", return_value=True),
            patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
        ):
            resp = client.get("/health")
        data = resp.json()
        assert "status" in data
        assert "db" in data
        assert "gemini" in data
        assert data["status"] == "ok"

    def test_health_gemini_false_when_no_key(self, client):
        import os
        env_without_key = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
        with (
            patch("api.routes.health.connect_db"),
            patch("api.routes.health.verify_database_schema", return_value=True),
            patch.dict("os.environ", env_without_key, clear=True),
        ):
            resp = client.get("/health")
        assert resp.json()["gemini"] is False


# ---------------------------------------------------------------------------
# /keywords/research
# ---------------------------------------------------------------------------
class TestKeywordsResearchRoute:
    def _mock_keywords(self):
        from src.schemas import KeywordSuggestion
        from src.data_quality import DataSource
        return [
            KeywordSuggestion(
                keyword="best coffee beans",
                volume=5000.0,
                cpc=1.2,
                competition=0.3,
                data_source=DataSource.ESTIMATED,
            )
        ]

    def test_research_returns_200(self, client):
        with (
            patch("api.routes.keywords.run_keyword_research", return_value=self._mock_keywords()),
            patch("api.routes.keywords.get_db_session"),
        ):
            resp = client.post("/keywords/research", json={"seed_keyword": "coffee", "max_keywords": 5})
        assert resp.status_code == 200

    def test_research_response_is_list(self, client):
        with (
            patch("api.routes.keywords.run_keyword_research", return_value=self._mock_keywords()),
            patch("api.routes.keywords.get_db_session"),
        ):
            resp = client.post("/keywords/research", json={"seed_keyword": "coffee", "max_keywords": 5})
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 1

    def test_research_502_on_api_error(self, client):
        from src.exceptions import KeylyticsAPIError
        with (
            patch("api.routes.keywords.run_keyword_research", side_effect=KeylyticsAPIError("upstream fail")),
            patch("api.routes.keywords.get_db_session"),
        ):
            resp = client.post("/keywords/research", json={"seed_keyword": "test", "max_keywords": 5})
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# /keywords/history
# ---------------------------------------------------------------------------
class TestKeywordsHistoryRoute:
    def test_history_returns_200(self, client):
        import pandas as pd
        mock_df = pd.DataFrame([{"keyword": "coffee", "volume": 5000}])
        with (
            patch("api.routes.keywords.fetch_past_results", return_value=mock_df),
            patch("api.routes.keywords.get_db_session"),
        ):
            resp = client.get("/keywords/history?limit=10")
        assert resp.status_code == 200

    def test_history_returns_list_of_dicts(self, client):
        import pandas as pd
        mock_df = pd.DataFrame([{"keyword": "coffee"}, {"keyword": "tea"}])
        with (
            patch("api.routes.keywords.fetch_past_results", return_value=mock_df),
            patch("api.routes.keywords.get_db_session"),
        ):
            resp = client.get("/keywords/history")
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# /intelligence/serp
# ---------------------------------------------------------------------------
class TestIntelligenceSerpRoute:
    def _mock_serp_result(self):
        from src.schemas import SerpAnalysisResult
        return SerpAnalysisResult(
            keyword="coffee",
            serp_data={},
            snippet_analysis={},
            paa_questions={},
            ranking_analysis={},
            content_gaps={},
            optimization_suggestions=[],
            summary="Test SERP summary",
        )

    def test_serp_returns_200(self, client):
        with (
            patch("api.routes.intelligence.run_serp", return_value=self._mock_serp_result()),
            patch("api.routes.intelligence.get_db_session"),
        ):
            resp = client.post("/intelligence/serp", json={"keyword": "coffee"})
        assert resp.status_code == 200

    def test_serp_alias_route_works(self, client):
        """Legacy /serp/analyze path must also work."""
        with (
            patch("api.routes.intelligence.run_serp", return_value=self._mock_serp_result()),
            patch("api.routes.intelligence.get_db_session"),
        ):
            resp = client.post("/intelligence/serp/analyze", json={"keyword": "coffee"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /intelligence/intent (new route — not in legacy routers)
# ---------------------------------------------------------------------------
class TestIntelligenceIntentRoute:
    def test_intent_returns_200(self, client):
        from src.schemas import IntentClassification
        mock_result = IntentClassification(keyword="coffee", intent="commercial", source="rule")
        with (
            patch("api.routes.intelligence.run_intent_classifier", return_value=mock_result),
            patch("api.routes.intelligence.get_db_session"),
        ):
            resp = client.post("/intelligence/intent", json={"keyword": "coffee"})
        assert resp.status_code == 200

    def test_intent_response_has_expected_fields(self, client):
        from src.schemas import IntentClassification
        mock_result = IntentClassification(keyword="coffee", intent="informational", source="gemini")
        with (
            patch("api.routes.intelligence.run_intent_classifier", return_value=mock_result),
            patch("api.routes.intelligence.get_db_session"),
        ):
            resp = client.post("/intelligence/intent", json={"keyword": "coffee"})
        data = resp.json()
        assert data["intent"] == "informational"
        assert data["source"] == "gemini"
