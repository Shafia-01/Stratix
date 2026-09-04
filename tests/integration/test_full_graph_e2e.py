"""
End-to-end integration test for the full LangGraph research pipeline.

Drives the graph from START through plan_generation -> plan_approval (mocked
interrupt -> {"approved": True}) -> research_agent -> aggregator -> quality_gate
-> critic -> strategy_generation -> strategy_approval (mocked interrupt ->
{"approved": True}) -> persist -> END.

Regression guards:
 - status == "completed" at terminal state
 - ResearchRunLog row exists with status="completed" and non-null strategy_report
 - Exactly ONE LLM invocation for plan_generation_node
 - Exactly ONE LLM invocation for strategy_generation_node
   (Phase 1 fix: planner/strategy nodes must NOT call the LLM more than once
   per logical run; the critic node is also an LLM call but is separately tracked)

All LLM calls are intercepted by patching _get_llm in src.graph.nodes so no
real API requests are made. The research_agent_node (which uses create_react_agent)
is fully mocked at the graph-invoke level to avoid tool-call complexity.

Uses the existing tmp_db_path fixture from tests/conftest.py.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

import pytest

from src.db_client import connect_db
from src.models import ResearchRunLog
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers: minimal valid JSON responses for every LLM-calling node
# ---------------------------------------------------------------------------

_PLAN_JSON = json.dumps(
    {
        "seed_keyword": "organic coffee",
        "objectives": ["Find high-value keywords", "Identify market gaps"],
        "requested_modules": ["keyword_discovery", "serp_analysis"],
        "max_keywords": 5,
    }
)

_CRITIC_JSON = json.dumps(
    {
        "weak_claims": [],
        "data_gaps": [],
        "issues": [],
        "overall_verdict": "PASS",
        "critic_score": 0.9,
    }
)

_STRATEGY_JSON = json.dumps(
    {
        "seed_keyword": "organic coffee",
        "executive_summary": "Strong organic coffee market with clear growth opportunities.",
        "top_opportunities": [],
        "recommendations": [
            "Target informational queries around organic coffee brewing.",
            "Create comparison content for organic vs conventional coffee.",
            "Optimise for long-tail keywords with lower competition.",
            "Develop content around seasonal coffee trends.",
            "Build backlinks via coffee industry publications.",
        ],
        "version": "phase3",
    }
)


# ---------------------------------------------------------------------------
# Minimal collected_data that satisfies quality_gate + aggregator
# ---------------------------------------------------------------------------

_COLLECTED_DATA = {
    "keyword_research": {
        "items": [
            {
                "keyword": "organic coffee beans",
                "volume": 1200.0,
                "competition": 0.35,
                "cpc": 1.10,
                "score": 72.0,
                "difficulty": "Medium",
                "intent": "Commercial",
                "data_source": "unavailable",
                "trend_data_source": "unavailable",
            },
            {
                "keyword": "best organic coffee",
                "volume": 900.0,
                "competition": 0.40,
                "cpc": 0.95,
                "score": 65.0,
                "difficulty": "Easy",
                "intent": "Informational",
                "data_source": "unavailable",
                "trend_data_source": "unavailable",
            },
            {
                "keyword": "organic coffee benefits",
                "volume": 600.0,
                "competition": 0.28,
                "cpc": 0.75,
                "score": 58.0,
                "difficulty": "Easy",
                "intent": "Informational",
                "data_source": "unavailable",
                "trend_data_source": "unavailable",
            },
            {
                "keyword": "organic coffee guide",
                "volume": 400.0,
                "competition": 0.22,
                "cpc": 0.60,
                "score": 50.0,
                "difficulty": "Easy",
                "intent": "Informational",
                "data_source": "unavailable",
                "trend_data_source": "unavailable",
            },
            {
                "keyword": "organic coffee brewing",
                "volume": 300.0,
                "competition": 0.18,
                "cpc": 0.55,
                "score": 45.0,
                "difficulty": "Easy",
                "intent": "Informational",
                "data_source": "unavailable",
                "trend_data_source": "unavailable",
            },
        ]
    },
    "serp_analysis": {
        "serp_data": {
            "organic_results": [
                {"title": "Best Organic Coffee 2026"},
                {"title": "Organic Coffee Guide"},
                {"title": "Top Organic Coffee Brands"},
                {"title": "Organic Coffee Benefits"},
                {"title": "How to Choose Organic Coffee"},
            ]
        },
        "paa_questions": {
            "q1": "What is the best organic coffee?",
            "q2": "Is organic coffee healthier?",
        },
    },
}


# ---------------------------------------------------------------------------
# Helper: mock research_agent_node
# ---------------------------------------------------------------------------


def _mock_research_node(state):
    """
    Drop-in replacement for research_agent_node in the E2E test.

    Bypasses the real ReAct agent (which would need a live or heavily mocked
    LLM chain plus tool stubs) and returns deterministic collected_data that
    satisfies the quality gate (>=3 keywords, keyword_research confidence >= 0.3).
    """
    metadata = dict(state.get("execution_metadata") or {})
    return {
        **state,
        "collected_data": _COLLECTED_DATA,
        "status": "in_progress",
        "awaiting_human": False,
        "human_feedback": None,
        "messages": list(state.get("messages", [])),
        "execution_metadata": metadata,
        "errors": list(state.get("errors", [])),
        "retry_target_tools": None,
    }


# ---------------------------------------------------------------------------
# Main E2E test
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_full_graph_e2e_completes(tmp_db_path):
    """
    Full pipeline E2E:
      1. Build the real LangGraph with tmp SQLite DB as checkpointer.
      2. Mock _get_llm -> counting mock that returns valid JSON per node.
      3. Mock research_agent_node to inject deterministic collected_data.
      4. Mock interrupt() to return {"approved": True} (plan + report approval).
      5. Mock background evaluator to avoid secondary LLM calls.
      6. Invoke graph and drive through all interrupts.
      7. Assert: terminal status == "completed".
      8. Assert: ResearchRunLog row with status="completed" and strategy_report set.
      9. Assert: exactly ONE plan_generation LLM call (regression guard).
      10. Assert: exactly ONE strategy_generation LLM call (regression guard).
    """
    # ── Invocation counter per node ─────────────────────────────────────────
    counts: defaultdict[str, int] = defaultdict(int)

    def _make_response(content: str) -> AIMessage:
        # Return a real AIMessage so LangGraph's add_messages reducer
        # can serialize it without raising a TypeError.
        return AIMessage(content=content)

    def _smart_invoke(messages, *args, **kwargs):
        """Dispatch by inspecting the SystemMessage content."""
        from langchain_core.messages import SystemMessage

        system_content = ""
        for m in messages:
            if isinstance(m, SystemMessage):
                system_content = str(m.content)
                break

        if "Research Planner" in system_content:
            counts["plan_generation"] += 1
            return _make_response(_PLAN_JSON)
        elif "Critic Agent" in system_content:
            counts["critic"] += 1
            return _make_response(_CRITIC_JSON)
        elif "Strategy Agent" in system_content:
            counts["strategy_generation"] += 1
            return _make_response(_STRATEGY_JSON)
        else:
            counts["unknown"] += 1
            return _make_response(_STRATEGY_JSON)

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = _smart_invoke
    mock_llm.with_fallbacks.return_value = mock_llm

    run_id = str(uuid.uuid4())

    with (
        patch("src.graph.nodes._get_llm", return_value=mock_llm),
        patch("src.graph.nodes.interrupt", return_value={"approved": True}),
        # Patch in the graph module's namespace (where it's imported for add_node)
        patch("src.graph.graph.research_agent_node", side_effect=_mock_research_node),
        patch("src.evals.evaluator.KeylyticsEvaluator") as mock_eval_cls,
    ):
        mock_eval_inst = MagicMock()
        mock_eval_inst.evaluate_plan.return_value = MagicMock(score=0.85)
        mock_eval_inst.evaluate_report.return_value = MagicMock(score=0.80)
        mock_eval_inst.evaluate_tool_reliability.return_value = MagicMock(score=0.90)
        mock_eval_cls.return_value = mock_eval_inst

        from src.graph.graph import build_graph
        from src.graph.tracing import build_initial_metadata, get_run_config

        graph = build_graph()
        config = get_run_config("organic coffee", run_id)

        initial_state = {
            "seed_keyword": "organic coffee",
            "status": "pending",
            "awaiting_human": False,
            "messages": [],
            "errors": [],
            "execution_metadata": build_initial_metadata(run_id),
            "human_feedback": {"approved": True},
        }

        result = graph.invoke(initial_state, config)
        current = graph.get_state(config)
        state_vals = current.values if current else result

        # Drive through any remaining interrupts
        max_resumes = 5
        resumes = 0
        while (
            state_vals.get("status") in ("awaiting_approval", "in_progress")
            and resumes < max_resumes
        ):
            graph.update_state(
                config,
                {"human_feedback": {"approved": True}, "awaiting_human": False},
            )
            result = graph.invoke(None, config)
            current = graph.get_state(config)
            state_vals = current.values if current else result
            resumes += 1

    # ── Assertion 1: terminal state is "completed" ──────────────────────────
    final_status = state_vals.get("status", "unknown")
    assert final_status == "completed", (
        f"Expected status='completed', got status={final_status!r}. "
        f"Errors: {state_vals.get('errors', [])}"
    )

    # ── Assertion 2: ResearchRunLog row exists with correct data ────────────
    engine = connect_db()
    with Session(engine) as session:
        log_row = (
            session.query(ResearchRunLog)
            .filter(ResearchRunLog.run_id == run_id)
            .first()
        )

    assert log_row is not None, (
        f"Expected a ResearchRunLog row for run_id={run_id!r} but none was found."
    )
    assert log_row.status == "completed", (
        f"ResearchRunLog.status expected='completed', got={log_row.status!r}"
    )
    assert log_row.strategy_report is not None, (
        "ResearchRunLog.strategy_report must not be NULL after a completed run."
    )

    # ── Assertion 3: LLM invocation counts (Phase 1 regression guard) ───────
    plan_calls = counts.get("plan_generation", 0)
    strategy_calls = counts.get("strategy_generation", 0)

    assert plan_calls == 1, (
        f"Expected exactly 1 LLM call for plan_generation_node, got {plan_calls}. "
        "This guards against the Phase 1 regression where planner was called twice."
    )
    assert strategy_calls == 1, (
        f"Expected exactly 1 LLM call for strategy_generation_node, got {strategy_calls}. "
        "This guards against the Phase 1 regression where strategy was generated twice."
    )
