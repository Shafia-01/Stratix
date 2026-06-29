"""
Tests for GET /health endpoint.
The health response now includes db and gemini readiness booleans.
"""

from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_api_health_status_ok():
    """Health endpoint always returns status=ok with HTTP 200."""
    with (
        patch("api.routes.health.connect_db"),
        patch("api.routes.health.verify_database_schema", return_value=True),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
    ):
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "db" in data
    assert "gemini" in data


def test_api_health_db_false_when_db_unavailable():
    """db flag is False when the database is unreachable."""
    with (
        patch("api.routes.health.connect_db", side_effect=Exception("no db")),
        patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
    ):
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["db"] is False


def test_api_health_gemini_false_when_key_missing():
    """gemini flag is False when GEMINI_API_KEY env var is absent."""
    with (
        patch("api.routes.health.connect_db"),
        patch("api.routes.health.verify_database_schema", return_value=True),
        patch.dict("os.environ", {}, clear=False),
    ):
        import os
        os.environ.pop("GEMINI_API_KEY", None)
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["gemini"] is False
