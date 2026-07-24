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


class MockState:
    def __init__(self, values, next_nodes, checkpoint_id="completed"):
        self.values = values
        self.next = next_nodes
        self.config = {"configurable": {"checkpoint_id": checkpoint_id}}


def test_event_generator_retry_success(mock_compiled_graph):
    import asyncio

    async def mock_astream_events(*args, **kwargs):
        if False:
            yield None

    mock_compiled_graph.astream_events = mock_astream_events

    state_unresolved = MockState(values={"status": "in_progress"}, next_nodes=[])
    state_resolved = MockState(values={"status": "completed"}, next_nodes=[])

    mock_compiled_graph.get_state.side_effect = [state_unresolved, state_unresolved, state_resolved]

    from api.routes.agent import event_generator, StreamRequest

    request = StreamRequest(seed_keyword="coffee")

    async def run():
        events = []
        async for event in event_generator(request):
            events.append(event)
        return events

    events = asyncio.run(run())
    assert len(events) >= 2
    assert '"event": "completed"' in events[-1]
    assert '"status": "completed"' in events[-1]
    assert mock_compiled_graph.get_state.call_count == 3


def test_event_generator_retry_exhausted(mock_compiled_graph):
    import asyncio

    async def mock_astream_events(*args, **kwargs):
        if False:
            yield None

    mock_compiled_graph.astream_events = mock_astream_events

    state_unresolved = MockState(values={"status": "in_progress"}, next_nodes=[])
    mock_compiled_graph.get_state.return_value = state_unresolved

    from api.routes.agent import event_generator, StreamRequest

    request = StreamRequest(seed_keyword="coffee")

    async def run():
        events = []
        async for event in event_generator(request):
            events.append(event)
        return events

    with patch("api.routes.agent.logger") as mock_logger:
        events = asyncio.run(run())

    assert len(events) >= 2
    assert '"status": "in_progress"' in events[-1]
    mock_logger.warning.assert_called()
    assert any("Retry budget exhausted" in arg[0] for arg, _ in mock_logger.warning.call_args_list)


def test_event_generator_disconnect_in_finally(mock_compiled_graph):
    import asyncio

    async def mock_astream_events(*args, **kwargs):
        if False:
            yield None

    mock_compiled_graph.astream_events = mock_astream_events

    state_resolved = MockState(values={"status": "completed"}, next_nodes=[])
    mock_compiled_graph.get_state.return_value = state_resolved

    from api.routes.agent import event_generator, StreamRequest

    request = StreamRequest(seed_keyword="coffee")

    async def run():
        gen = event_generator(request)
        first_event = await gen.__anext__()
        assert "run_started" in first_event
        await gen.aclose()

    asyncio.run(run())
