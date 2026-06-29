"""
Unit tests for Keylytics LangGraph node functions.

Tests:
  1. planner_node: valid LLM JSON → research_plan populated, status="awaiting_approval"
  2. planner_node: malformed JSON → fallback plan used
  3. aggregator_node: keyword items present → keyword_findings populated, confidence_scores correct
  4. aggregator_node: keyword_research missing → confidence_scores["keyword_research"]==0.0
  5. strategy_agent_node: valid LLM JSON → strategy_report populated, schema-validated
  6. persist_node: mock save_to_db → status="completed", end_ts set in execution_metadata
  7. route_after_plan: approved=True → "research_agent_node"; approved=False → "__end__"
  8. route_after_research: no keyword_research in collected_data → "__end__"

All tests use pytest-mock (mocker fixture). No real API calls are made.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.graph.nodes import (
    aggregator_node,
    persist_node,
    planner_node,
    route_after_plan,
    route_after_research,
    route_after_strategy,
    strategy_agent_node,
    critic_node,
    quality_gate_node,
    route_after_critic,
    route_after_quality_gate,
)
from src.graph.state import AgentState


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_state() -> AgentState:
    """Minimal valid AgentState for testing."""
    return {
        "seed_keyword": "content marketing",
        "research_plan": None,
        "collected_data": {},
        "intelligence_findings": None,
        "confidence_scores": {},
        "strategy_report": None,
        "status": "pending",
        "errors": [],
        "execution_metadata": {
            "run_id": "test-run-001",
            "planner_retries": 0,
            "strategy_retries": 0,
            "tool_call_counts": {},
            "start_ts": "2026-01-01T00:00:00Z",
            "end_ts": None,
        },
        "messages": [],
        "awaiting_human": False,
        "human_feedback": None,
    }


@pytest.fixture
def mock_llm():
    """Patch _get_llm in nodes.py and return the mock LLM instance."""
    with patch("src.graph.nodes._get_llm") as mock_factory:
        mock_chat = MagicMock()
        mock_factory.return_value = mock_chat
        yield mock_chat


# ---------------------------------------------------------------------------
# Test 1: planner_node — valid LLM response
# ---------------------------------------------------------------------------

def test_planner_node_valid_llm_response(base_state, mock_llm):
    """
    Given a valid JSON plan from the LLM,
    planner_node should populate research_plan and set status="awaiting_approval".
    """
    valid_plan = {
        "seed_keyword": "content marketing",
        "objectives": ["Identify high-volume keywords", "Analyse competitor gaps"],
        "requested_modules": ["keyword_discovery", "serp_analysis", "competitor_gap"],
        "max_keywords": 10,
    }
    mock_response = MagicMock()
    mock_response.content = json.dumps(valid_plan)
    mock_llm.invoke.return_value = mock_response

    with patch("src.graph.nodes.interrupt", return_value=None):
        result = planner_node(base_state)

    assert result["research_plan"]["seed_keyword"] == "content marketing"
    assert result["research_plan"]["max_keywords"] == 10
    assert "keyword_discovery" in result["research_plan"]["requested_modules"]
    assert result["status"] == "awaiting_approval"
    assert result["awaiting_human"] is True
    assert result["execution_metadata"]["planner_retries"] == 1


# ---------------------------------------------------------------------------
# Test 2: planner_node — malformed JSON falls back to default plan
# ---------------------------------------------------------------------------

def test_planner_node_malformed_json_uses_fallback(base_state, mock_llm):
    """
    When the LLM returns invalid JSON,
    planner_node should use the fallback plan (keyword_discovery + competitor_gap + serp_analysis).
    """
    mock_response = MagicMock()
    mock_response.content = "This is definitely not JSON {broken"
    mock_llm.invoke.return_value = mock_response

    with patch("src.graph.nodes.interrupt", return_value=None):
        result = planner_node(base_state)

    plan = result["research_plan"]
    assert plan["seed_keyword"] == "content marketing"
    assert "keyword_discovery" in plan["requested_modules"]
    assert plan["max_keywords"] == 10
    assert result["status"] == "awaiting_approval"
    # response should be None → messages should include the fallback SystemMessage
    messages = result["messages"]
    # Last message should be a SystemMessage (fallback)
    from langchain_core.messages import SystemMessage
    assert any(isinstance(m, SystemMessage) for m in messages)


# ---------------------------------------------------------------------------
# Test 3: aggregator_node — keyword items present
# ---------------------------------------------------------------------------

def test_aggregator_node_with_keyword_items(base_state):
    """
    When collected_data contains valid keyword_research items,
    aggregator_node should populate keyword_findings and compute confidence_scores.
    """
    state = dict(base_state)
    state["research_plan"] = {
        "seed_keyword": "content marketing",
        "requested_modules": ["keyword_discovery", "serp_analysis"],
        "max_keywords": 5,
    }
    state["collected_data"] = {
        "keyword_research": {
            "items": [
                {
                    "keyword": "content marketing strategy",
                    "volume": 1000,
                    "competition": 0.4,
                    "cpc": 2.5,
                    "score": 75.0,
                    "difficulty": "Medium",
                    "intent": "Informational",
                    "data_source": "unavailable",
                    "trend_data_source": "unavailable",
                },
                {
                    "keyword": "content marketing tools",
                    "volume": 500,
                    "competition": 0.6,
                    "cpc": 3.0,
                    "score": 60.0,
                    "difficulty": "Hard",
                    "intent": "Commercial",
                    "data_source": "unavailable",
                    "trend_data_source": "unavailable",
                },
            ]
        },
        "serp_analysis": {
            "serp_data": {
                "organic_results": [
                    {"title": "Result 1"},
                    {"title": "Result 2"},
                    {"title": "Result 3"},
                    {"title": "Result 4"},
                    {"title": "Result 5"},
                ]
            },
            "paa_questions": {"q1": "What is content marketing?", "q2": "How to start?"},
        },
    }

    result = aggregator_node(state)

    findings = result["intelligence_findings"]
    assert len(findings["keyword_findings"]) == 2
    assert findings["keyword_findings"][0]["keyword"] == "content marketing strategy"

    scores = result["confidence_scores"]
    # 2/5 = 0.4 fill ratio, avg_volume=750>0 → base=1.0 → 0.4*1.0=0.4
    assert scores["keyword_research"] == pytest.approx(0.4, abs=0.01)
    # 5 organic + 2 PAA → 1.0
    assert scores["serp_analysis"] == pytest.approx(1.0)

    # Fix 5: human_feedback cleared
    assert result["human_feedback"] is None


# ---------------------------------------------------------------------------
# Test 4: aggregator_node — missing keyword_research
# ---------------------------------------------------------------------------

def test_aggregator_node_missing_keyword_research(base_state):
    """
    When keyword_research is absent from collected_data,
    confidence_scores["keyword_research"] should be 0.0 and an error added.
    """
    state = dict(base_state)
    state["research_plan"] = {
        "seed_keyword": "content marketing",
        "requested_modules": ["keyword_discovery"],
        "max_keywords": 10,
    }
    state["collected_data"] = {}  # empty — no keyword_research

    result = aggregator_node(state)

    assert result["confidence_scores"]["keyword_research"] == 0.0
    assert any("keyword_research" in err for err in result["errors"])
    assert result["intelligence_findings"]["keyword_findings"] == []


# ---------------------------------------------------------------------------
# Test 5: strategy_agent_node — valid LLM response
# ---------------------------------------------------------------------------

def test_strategy_agent_node_valid_response(base_state, mock_llm):
    """
    When the LLM returns a valid strategy report JSON,
    strategy_agent_node should populate strategy_report with schema-validated data.
    """
    state = dict(base_state)
    state["intelligence_findings"] = {
        "seed_keyword": "content marketing",
        "keyword_findings": [],
        "competitor_gap": None,
        "topic_clusters": None,
        "trend_forecast": None,
        "serp_analysis": None,
    }
    state["confidence_scores"] = {"keyword_research": 0.8}
    state["research_plan"] = {
        "seed_keyword": "content marketing",
        "objectives": ["Find keywords"],
        "requested_modules": ["keyword_discovery"],
        "max_keywords": 10,
    }

    valid_report = {
        "seed_keyword": "content marketing",
        "executive_summary": "Content marketing is a highly competitive space with significant opportunities.",
        "top_opportunities": [],
        "recommendations": [
            "Target long-tail keywords with high informational intent.",
            "Create pillar content around core topic clusters.",
            "Optimise meta descriptions for SERP CTR improvement.",
            "Analyse competitor backlink profiles for link-building opportunities.",
            "Launch video content to capture mixed-media SERP features.",
        ],
        "version": "phase3",
    }
    mock_response = MagicMock()
    mock_response.content = json.dumps(valid_report)
    mock_llm.invoke.return_value = mock_response

    with patch("src.graph.nodes.interrupt", return_value=None):
        result = strategy_agent_node(state)

    assert result["strategy_report"]["seed_keyword"] == "content marketing"
    assert len(result["strategy_report"]["recommendations"]) == 5
    assert result["status"] == "awaiting_approval"
    assert result["awaiting_human"] is True
    assert result["execution_metadata"]["strategy_retries"] == 1


# ---------------------------------------------------------------------------
# Test 6: persist_node — mock save_to_db → status="completed"
# ---------------------------------------------------------------------------

def test_persist_node_saves_and_completes(base_state, mocker):
    """
    persist_node should call save_to_db, set status="completed",
    and stamp end_ts in execution_metadata.
    """
    state = dict(base_state)
    state["intelligence_findings"] = {
        "seed_keyword": "content marketing",
        "keyword_findings": [
            {
                "seed": "content marketing",
                "keyword": "content marketing strategy",
                "volume": 1000.0,
                "competition": 0.4,
                "cpc": 2.5,
                "trend": None,
                "score": 75.0,
                "difficulty": "Medium",
                "intent": "Informational",
                "competitors": [],
                "data_source": "unavailable",
                "trend_data_source": "unavailable",
            }
        ],
    }

    mock_save = mocker.patch("src.graph.nodes.persist_node.__module__")  # noqa
    # Patch where save_to_db is imported in nodes.py (inside try block)
    mocker.patch("src.db_client.save_to_db", return_value=None)

    # Patch evaluator to avoid LLM calls in unit test
    mock_eval = mocker.MagicMock()
    mock_eval.evaluate_plan.return_value = MagicMock(score=0.8)
    mock_eval.evaluate_report.return_value = MagicMock(score=0.75)
    mock_eval.evaluate_tool_reliability.return_value = MagicMock(score=0.9)
    mocker.patch("src.evals.evaluator.KeylyticsEvaluator", return_value=mock_eval)

    result = persist_node(state)

    assert result["status"] == "completed"
    assert result["awaiting_human"] is False
    assert result["execution_metadata"]["end_ts"] is not None
    # Fix 5: human_feedback cleared
    assert result["human_feedback"] is None


# ---------------------------------------------------------------------------
# Test 7: route_after_plan routing logic
# ---------------------------------------------------------------------------

def test_route_after_plan_approved():
    """approved=True should route to research_agent_node."""
    state: AgentState = {"human_feedback": {"approved": True}}
    assert route_after_plan(state) == "research_agent_node"


def test_route_after_plan_rejected():
    """No approval and no edited_plan should route to __end__."""
    state: AgentState = {"human_feedback": {"approved": False}}
    assert route_after_plan(state) == "__end__"


def test_route_after_plan_edited_within_retry_limit():
    """edited_plan with retries < 2 should route back to planner_node."""
    state: AgentState = {
        "human_feedback": {"edited_plan": {"seed_keyword": "test"}},
        "execution_metadata": {"planner_retries": 1},
    }
    assert route_after_plan(state) == "planner_node"


def test_route_after_plan_edited_at_retry_limit():
    """edited_plan with retries >= 2 should route to __end__."""
    state: AgentState = {
        "human_feedback": {"edited_plan": {"seed_keyword": "test"}},
        "execution_metadata": {"planner_retries": 2},
    }
    assert route_after_plan(state) == "__end__"


def test_route_after_plan_null_feedback():
    """None feedback should route to __end__."""
    state: AgentState = {"human_feedback": None}
    assert route_after_plan(state) == "__end__"


# ---------------------------------------------------------------------------
# Test 8: route_after_research routing logic
# ---------------------------------------------------------------------------

def test_route_after_research_no_keyword_data():
    """Empty collected_data should route to __end__."""
    state: AgentState = {"collected_data": {}}
    assert route_after_research(state) == "__end__"


def test_route_after_research_keyword_error():
    """keyword_research with an error key should route to __end__."""
    state: AgentState = {
        "collected_data": {"keyword_research": {"error": "API failure"}}
    }
    assert route_after_research(state) == "__end__"


def test_route_after_research_valid_data():
    """Valid keyword_research data should route to aggregator_node."""
    state: AgentState = {
        "collected_data": {
            "keyword_research": {"items": [{"keyword": "test", "volume": 100}]}
        }
    }
    assert route_after_research(state) == "aggregator_node"


# ---------------------------------------------------------------------------
# Bonus: route_after_strategy
# ---------------------------------------------------------------------------

def test_route_after_strategy_approved():
    """approved=True should route to persist_node."""
    state: AgentState = {
        "human_feedback": {"approved": True},
        "execution_metadata": {"strategy_retries": 0},
    }
    assert route_after_strategy(state) == "persist_node"


def test_route_after_strategy_regenerate_within_limit():
    """regenerate=True with retries < 1 should route back to strategy_agent_node."""
    state: AgentState = {
        "human_feedback": {"regenerate": True},
        "execution_metadata": {"strategy_retries": 0},
    }
    assert route_after_strategy(state) == "strategy_agent_node"


def test_route_after_strategy_regenerate_at_limit():
    """regenerate=True with retries >= 1 should route to persist_node."""
    state: AgentState = {
        "human_feedback": {"regenerate": True},
        "execution_metadata": {"strategy_retries": 1},
    }
    assert route_after_strategy(state) == "persist_node"


# ---------------------------------------------------------------------------
# Critic Node Tests
# ---------------------------------------------------------------------------

def test_critic_node_pass_verdict(base_state, mock_llm):
    """If the LLM returns PASS verdict, critic_node should store the feedback in state."""
    state = dict(base_state)
    state["intelligence_findings"] = {
        "seed_keyword": "test",
        "keyword_findings": [{"keyword": "kw1"}, {"keyword": "kw2"}, {"keyword": "kw3"}]
    }
    state["confidence_scores"] = {"keyword_research": 0.8}

    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "weak_claims": [],
        "data_gaps": [],
        "issues": [],
        "overall_verdict": "PASS",
        "critic_score": 0.9
    })
    mock_llm.invoke.return_value = mock_response

    result = critic_node(state)

    assert result["critic_feedback"]["overall_verdict"] == "PASS"
    assert result["critic_feedback"]["critic_score"] == 0.9
    assert result["execution_metadata"]["critic_retries"] == 1


def test_critic_node_revise_verdict(base_state, mock_llm):
    """If LLM returns REVISE verdict, critic_node stores feedback."""
    state = dict(base_state)
    state["intelligence_findings"] = {
        "seed_keyword": "test",
        "keyword_findings": [{"keyword": "kw1"}]
    }
    state["confidence_scores"] = {"keyword_research": 0.2}

    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "weak_claims": ["Low keyword count"],
        "data_gaps": ["keyword_research confidence is low"],
        "issues": ["Incomplete findings"],
        "overall_verdict": "REVISE",
        "critic_score": 0.3
    })
    mock_llm.invoke.return_value = mock_response

    result = critic_node(state)

    assert result["critic_feedback"]["overall_verdict"] == "REVISE"
    assert result["critic_feedback"]["critic_score"] == 0.3
    assert len(result["critic_feedback"]["issues"]) == 1


def test_critic_node_llm_failure_defaults_to_pass(base_state, mock_llm):
    """If LLM invoke raises Exception, critic_node defaults to PASS without state corruption."""
    state = dict(base_state)
    mock_llm.invoke.side_effect = Exception("LLM connection error")

    result = critic_node(state)

    assert result["critic_feedback"]["overall_verdict"] == "PASS"
    assert result["critic_feedback"]["critic_score"] == 0.5
    assert "Critic evaluation failed" in result["critic_feedback"]["issues"][0]


def test_route_after_critic_pass():
    """overall_verdict=PASS should route to strategy_agent_node."""
    state: AgentState = {
        "critic_feedback": {"overall_verdict": "PASS"},
        "execution_metadata": {"critic_retries": 1}
    }
    assert route_after_critic(state) == "strategy_agent_node"


def test_route_after_critic_revise_with_retries():
    """overall_verdict=REVISE and retries <= 1 should route to research_agent_node."""
    state: AgentState = {
        "critic_feedback": {"overall_verdict": "REVISE"},
        "execution_metadata": {"critic_retries": 1}
    }
    assert route_after_critic(state) == "research_agent_node"


def test_route_after_critic_revise_max_retries():
    """overall_verdict=REVISE and retries > 1 should route to strategy_agent_node."""
    state: AgentState = {
        "critic_feedback": {"overall_verdict": "REVISE"},
        "execution_metadata": {"critic_retries": 2}
    }
    assert route_after_critic(state) == "strategy_agent_node"


# ---------------------------------------------------------------------------
# Quality Gate Node Tests
# ---------------------------------------------------------------------------

def test_quality_gate_passes_on_good_data(base_state):
    """If keyword_research confidence >= 0.3 and count >= 3, gate passes."""
    state = dict(base_state)
    state["confidence_scores"] = {"keyword_research": 0.8, "serp_analysis": 0.9}
    state["intelligence_findings"] = {
        "keyword_findings": [{"keyword": "kw1"}, {"keyword": "kw2"}, {"keyword": "kw3"}]
    }

    result = quality_gate_node(state)
    summary = result["execution_metadata"]["data_quality_summary"]

    assert summary["gate_passed"] is True
    assert len(summary["data_limitations"]) == 0


def test_quality_gate_fails_on_low_confidence(base_state):
    """If keyword_research confidence < 0.3, gate fails and limitations populated."""
    state = dict(base_state)
    state["confidence_scores"] = {"keyword_research": 0.2}
    state["intelligence_findings"] = {
        "keyword_findings": [{"keyword": "kw1"}, {"keyword": "kw2"}, {"keyword": "kw3"}]
    }

    result = quality_gate_node(state)
    summary = result["execution_metadata"]["data_quality_summary"]

    assert summary["gate_passed"] is False
    assert any("confidence" in lim for lim in summary["data_limitations"])
    assert len(result["errors"]) > 0


def test_quality_gate_fails_on_few_keywords(base_state):
    """If keyword findings count < 3, gate fails."""
    state = dict(base_state)
    state["confidence_scores"] = {"keyword_research": 0.8}
    state["intelligence_findings"] = {
        "keyword_findings": [{"keyword": "kw1"}]
    }

    result = quality_gate_node(state)
    summary = result["execution_metadata"]["data_quality_summary"]

    assert summary["gate_passed"] is False
    assert any("keywords found" in lim for lim in summary["data_limitations"])


def test_route_after_quality_gate_retries_once():
    """If gate fails, route back to research if gate_retries == 0, else route to critic."""
    # Retry budget remains
    state: AgentState = {
        "execution_metadata": {
            "data_quality_summary": {"gate_passed": False},
            "gate_retries": 0
        }
    }
    assert route_after_quality_gate(state) == "research_agent_node"

    # Retry budget exhausted
    state = {
        "execution_metadata": {
            "data_quality_summary": {"gate_passed": False},
            "gate_retries": 1
        }
    }
    assert route_after_quality_gate(state) == "critic_node"

    # Gate passed
    state = {
        "execution_metadata": {
            "data_quality_summary": {"gate_passed": True},
            "gate_retries": 0
        }
    }
    assert route_after_quality_gate(state) == "critic_node"

