import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

@pytest.fixture
def mock_compiled_graph():
    with patch("api.routes.agent.get_compiled_graph") as mock_get:
        mock_graph = MagicMock()
        mock_get.return_value = mock_graph
        yield mock_graph

def test_start_agent_run_success(mock_compiled_graph):
    # Set up mock state returned by graph
    mock_compiled_graph.invoke.return_value = {
        "status": "awaiting_approval",
        "awaiting_human": True,
        "research_plan": {
            "seed_keyword": "organic coffee",
            "objectives": ["Find keywords"],
            "requested_modules": ["keyword_discovery"],
            "max_keywords": 10
        }
    }
    
    mock_compiled_graph.get_state.return_value = MagicMock(
        values={
            "status": "awaiting_approval",
            "awaiting_human": True,
            "research_plan": {
                "seed_keyword": "organic coffee",
                "objectives": ["Find keywords"],
                "requested_modules": ["keyword_discovery"],
                "max_keywords": 10
            }
        }
    )

    response = client.post("/agent/run", json={"seed_keyword": "organic coffee"})
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "awaiting_approval"
    assert data["awaiting_human"] is True
    assert data["checkpoint_data"]["research_plan"]["seed_keyword"] == "organic coffee"

def test_resume_agent_run_success(mock_compiled_graph):
    # Set up mock state returned by graph after resuming
    mock_compiled_graph.invoke.return_value = {
        "status": "completed",
        "awaiting_human": False
    }
    mock_compiled_graph.get_state.return_value = MagicMock(
        values={
            "status": "completed",
            "awaiting_human": False
        }
    )

    response = client.post("/agent/resume", json={
        "run_id": "test-run-id",
        "human_feedback": {"approved": True}
    })
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "test-run-id"
    assert data["status"] == "completed"
    assert data["awaiting_human"] is False

def test_get_run_status_not_found(mock_compiled_graph):
    mock_compiled_graph.get_state.return_value = None

    response = client.get("/agent/status/nonexistent-id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_get_run_status_success(mock_compiled_graph):
    mock_compiled_graph.get_state.return_value = MagicMock(
        values={
            "status": "in_progress",
            "awaiting_human": False,
            "execution_metadata": {"run_id": "test-run-id"},
            "errors": [],
            "confidence_scores": {}
        }
    )

    response = client.get("/agent/status/test-run-id")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "test-run-id"
    assert data["status"] == "in_progress"
    assert data["awaiting_human"] is False
