"""Tests for aggregator_node — the only deterministic graph node."""
import pytest
from unittest.mock import patch
from src.graph.nodes import aggregator_node


def _base_state():
    return {
        "seed_keyword": "AI tools",
        "research_plan": {
            "seed_keyword": "AI tools",
            "objectives": ["test"],
            "requested_modules": ["keyword_discovery", "serp_analysis", "competitor_gap"],
            "max_keywords": 5,
        },
        "collected_data": {
            "keyword_research": {
                "items": [
                    {
                        "keyword": "AI writing tools",
                        "volume": 5000.0,
                        "competition": 0.4,
                        "cpc": 2.5,
                        "score": 0.75,
                        "difficulty": "Medium",
                        "intent": "Commercial",
                        "data_source": "live",
                        "trend_data_source": "unavailable",
                    },
                    {
                        "keyword": "best AI tools",
                        "volume": 8000.0,
                        "competition": 0.6,
                        "cpc": 3.0,
                        "score": 0.82,
                        "difficulty": "Easy",
                        "intent": "Commercial",
                        "data_source": "live",
                        "trend_data_source": "unavailable",
                    },
                ]
            },
            "serp_analysis": {
                "serp_data": {
                    "organic_results": [{"title": "Test", "link": "https://example.com"}]
                }
            },
            "competitor_gap": {
                "opportunities": [
                    {
                        "keyword": "AI tool comparison",
                        "opportunity_type": "keyword_gap",
                        "gap_score": 85.0,
                        "traffic_potential": "high",
                        "reasoning": "No competitors rank here.",
                    }
                ]
            },
        },
        "status": "in_progress",
        "awaiting_human": False,
        "messages": [],
        "errors": [],
        "execution_metadata": {"planner_retries": 0, "strategy_retries": 0},
    }


def test_aggregator_builds_intelligence_findings():
    state = _base_state()
    result = aggregator_node(state)

    assert result["intelligence_findings"] is not None
    findings = result["intelligence_findings"]
    assert findings["seed_keyword"] == "AI tools"
    assert len(findings["keyword_findings"]) == 2
    assert findings["keyword_findings"][0]["keyword"] == "AI writing tools"


def test_aggregator_computes_confidence_scores():
    state = _base_state()
    result = aggregator_node(state)

    scores = result["confidence_scores"]
    assert "keyword_research" in scores
    # 2 keywords returned out of 5 requested → 0.4
    assert scores["keyword_research"] == pytest.approx(0.4, abs=0.01)
    # serp_analysis has organic results → 1.0
    assert scores["serp_analysis"] == 1.0
    # competitor_gap has opportunities → 1.0
    assert scores["competitor_gap"] == 1.0


def test_aggregator_handles_missing_keyword_research():
    state = _base_state()
    state["collected_data"].pop("keyword_research")
    result = aggregator_node(state)

    assert result["confidence_scores"].get("keyword_research", 0.0) == 0.0
    assert any("keyword_research" in e for e in result["errors"])


def test_aggregator_handles_error_tool_result():
    state = _base_state()
    state["collected_data"]["serp_analysis"] = {"error": "SERPAPI_KEY not found"}
    result = aggregator_node(state)

    # serp_analysis should get low confidence (0.3) since no organic_results
    assert result["confidence_scores"].get("serp_analysis", 1.0) == pytest.approx(0.3, abs=0.01)


def test_aggregator_empty_collected_data():
    state = _base_state()
    state["collected_data"] = {}
    result = aggregator_node(state)

    assert result["intelligence_findings"]["keyword_findings"] == []
    assert result["confidence_scores"].get("keyword_research", 1.0) == 0.0
    assert len(result["errors"]) > 0
