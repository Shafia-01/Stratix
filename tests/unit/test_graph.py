import pytest
from unittest.mock import MagicMock, patch
from src.graph.nodes import (
    planner_node,
    aggregator_node,
    route_after_plan,
    route_after_research,
    route_after_strategy,
)
from src.graph.state import AgentState

@pytest.fixture
def mock_llm():
    with patch("src.graph.nodes._get_llm") as mock_get:
        mock_chat = MagicMock()
        mock_get.return_value = mock_chat
        yield mock_chat

@pytest.fixture
def base_state() -> AgentState:
    return {
        "seed_keyword": "coffee",
        "research_plan": None,
        "collected_data": {},
        "intelligence_findings": None,
        "strategy_report": None,
        "status": "pending",
        "errors": [],
        "execution_metadata": {
            "run_id": "test-run-id",
            "planner_retries": 0,
            "strategy_retries": 0,
            "tool_call_counts": {},
        },
        "messages": [],
        "awaiting_human": False,
    }

def test_planner_node_human_edited_plan(base_state):
    # If the user edited the plan, it should use the human-edited plan without calling the LLM
    edited = {
        "seed_keyword": "coffee",
        "objectives": ["Custom Goal"],
        "requested_modules": ["keyword_discovery"],
        "max_keywords": 5,
    }
    state = base_state.copy()
    state["human_feedback"] = {"edited_plan": edited}
    
    with patch("src.graph.nodes.interrupt"):
        res = planner_node(state)
        # Should not interrupt again if it just uses the edited plan
        assert res["research_plan"]["seed_keyword"] == edited["seed_keyword"]
        assert res["research_plan"]["max_keywords"] == edited["max_keywords"]
        assert res["research_plan"]["requested_modules"] == edited["requested_modules"]
        assert res["status"] == "awaiting_approval"
        assert res["awaiting_human"] is True
        assert res["execution_metadata"]["planner_retries"] == 1
        assert res["human_feedback"] is None

def test_planner_node_llm_flow(base_state, mock_llm):
    # Set up LLM return value
    mock_response = MagicMock()
    mock_response.content = """
    {
      "seed_keyword": "coffee",
      "objectives": ["Objective 1"],
      "requested_modules": ["keyword_discovery", "serp_analysis"],
      "max_keywords": 12
    }
    """
    mock_llm.invoke.return_value = mock_response

    state = base_state.copy()
    with patch("src.graph.nodes.interrupt") as mock_interrupt:
        res = planner_node(state)
        assert res["research_plan"]["max_keywords"] == 12
        assert "keyword_discovery" in res["research_plan"]["requested_modules"]
        assert res["status"] == "awaiting_approval"
        assert res["awaiting_human"] is True
        mock_interrupt.assert_called_once()

def test_aggregator_node_success(base_state):
    state = base_state.copy()
    state["collected_data"] = {
        "keyword_research": {
            "items": [
                {"keyword": "best coffee", "volume": 1000, "competition": 0.5, "cpc": 1.5}
            ]
        },
        "serp_analysis": {
            "serp_data": {"organic_results": [{"title": "Organic Coffee"}]}
        }
    }
    state["research_plan"] = {
        "seed_keyword": "coffee",
        "requested_modules": ["keyword_discovery", "serp_analysis"],
        "max_keywords": 5
    }
    
    res = aggregator_node(state)
    assert res["confidence_scores"]["keyword_research"] == 0.2  # 1/5
    assert res["confidence_scores"]["serp_analysis"] == 0.2
    assert len(res["intelligence_findings"]["keyword_findings"]) == 1

def test_route_after_plan():
    state: AgentState = {"human_feedback": {"approved": True}}
    assert route_after_plan(state) == "research_agent_node"

    state = {"human_feedback": {"edited_plan": {"seed_keyword": "coffee"}}, "execution_metadata": {"planner_retries": 1}}
    assert route_after_plan(state) == "planner_node"

    state = {"human_feedback": {"edited_plan": {"seed_keyword": "coffee"}}, "execution_metadata": {"planner_retries": 2}}
    assert route_after_plan(state) == "__end__"

    state = {"human_feedback": None}
    assert route_after_plan(state) == "__end__"

def test_route_after_research():
    state: AgentState = {"collected_data": {"keyword_research": {"items": []}}}
    assert route_after_research(state) == "aggregator_node"

    state = {"collected_data": {}}
    assert route_after_research(state) == "__end__"

    state = {"collected_data": {"keyword_research": {"error": "Failed"}}}
    assert route_after_research(state) == "__end__"

def test_route_after_strategy():
    state: AgentState = {"human_feedback": {"regenerate": True}, "execution_metadata": {"strategy_retries": 0}}
    assert route_after_strategy(state) == "strategy_agent_node"

    state = {"human_feedback": {"regenerate": True}, "execution_metadata": {"strategy_retries": 1}}
    assert route_after_strategy(state) == "persist_node"

    state = {"human_feedback": {"approved": True}}
    assert route_after_strategy(state) == "persist_node"
