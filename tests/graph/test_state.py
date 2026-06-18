"""Tests that AgentState TypedDict can be instantiated and fields are correct."""
from src.graph.state import AgentState


def test_agent_state_minimal():
    state: AgentState = {
        "seed_keyword": "AI tools",
        "status": "pending",
        "awaiting_human": False,
        "messages": [],
        "errors": [],
    }
    assert state["seed_keyword"] == "AI tools"
    assert state["status"] == "pending"
    assert state["awaiting_human"] is False
    assert state["messages"] == []
    assert state["errors"] == []


def test_agent_state_with_plan():
    from datetime import datetime
    state: AgentState = {
        "seed_keyword": "SEO software",
        "research_plan": {
            "seed_keyword": "SEO software",
            "objectives": ["Find keywords", "Analyse SERP"],
            "requested_modules": ["keyword_discovery", "serp_analysis"],
            "max_keywords": 10,
            "created_at": datetime.utcnow().isoformat(),
        },
        "status": "awaiting_approval",
        "awaiting_human": True,
        "messages": [],
        "errors": [],
    }
    assert state["research_plan"]["max_keywords"] == 10
    assert "keyword_discovery" in state["research_plan"]["requested_modules"]


def test_agent_state_confidence_scores():
    state: AgentState = {
        "seed_keyword": "AI tools",
        "status": "in_progress",
        "awaiting_human": False,
        "messages": [],
        "errors": [],
        "confidence_scores": {
            "keyword_research": 0.8,
            "serp_analysis": 1.0,
            "competitor_gap": 0.6,
        },
    }
    assert state["confidence_scores"]["keyword_research"] == 0.8
    assert state["confidence_scores"]["serp_analysis"] == 1.0


def test_agent_state_critic_feedback():
    state: AgentState = {
        "seed_keyword": "AI tools",
        "status": "in_progress",
        "awaiting_human": False,
        "messages": [],
        "errors": [],
        "critic_feedback": {
            "weak_claims": ["claim1"],
            "data_gaps": ["gap1"],
            "issues": ["issue1"],
            "overall_verdict": "REVISE",
            "critic_score": 0.3
        },
        "critic_retries": 1
    }
    assert state["critic_feedback"]["overall_verdict"] == "REVISE"
    assert state["critic_feedback"]["critic_score"] == 0.3
    assert state["critic_retries"] == 1

