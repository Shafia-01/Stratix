"""
Unit tests for the _load_report_data() helper in src/ui/executive_reports.py.

Scenarios tested:
  (a) Checkpoint state present and populated  → source="checkpoint", rich data returned
  (b) Checkpoint state empty (no strategy_report) → ResearchRunLog fallback used
  (c) Checkpoint state raises exception       → ResearchRunLog fallback used
  (d) Both checkpoint and DB empty            → source="unavailable", no exception
  (e) DB fallback raises exception            → source="unavailable", error message set
  (f) DB row present but strategy_report is None → fallback returns "unavailable"
  (g) DB row present, strategy_report is malformed JSON → report={}, still returns db_fallback
      if confidence_scores is valid

All tests use unittest.mock — no real DB or LangGraph connections are made.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.ui.executive_reports import _load_report_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_REPORT = {
    "executive_summary": "Market looks bullish.",
    "top_opportunities": [{"keyword": "seo tools", "volume": 5000}],
    "recommendations": ["Invest in content."],
}

SAMPLE_CONFIDENCE = {"keyword_research": 0.85, "competitor_analysis": 0.6}

SAMPLE_FINDINGS = {"competitor_gap": {"opportunities": []}, "data_limitations": ["Limited SEMrush data"]}

SAMPLE_CRITIC = {"data_gaps": ["Missing trend data"], "weak_claims": []}


def _make_graph_with_state(strategy_report=None, confidence_scores=None,
                            intelligence_findings=None, critic_feedback=None,
                            execution_metadata=None, raise_exc=False):
    """Return a mock graph whose get_state() returns the given values."""
    graph = MagicMock()
    if raise_exc:
        graph.get_state.side_effect = RuntimeError("checkpointer unavailable")
        return graph

    state = MagicMock()
    if strategy_report is not None:
        state.values = {
            "strategy_report": strategy_report,
            "confidence_scores": confidence_scores or {},
            "intelligence_findings": intelligence_findings or {},
            "critic_feedback": critic_feedback or {},
            "execution_metadata": execution_metadata or {},
        }
    else:
        # Simulate empty checkpoint (no strategy_report key)
        state.values = {}

    graph.get_state.return_value = state
    return graph


def _make_engine_with_row(run_id, strategy_report=None, confidence_scores=None,
                           no_row=False, raise_exc=False):
    """Return a mock SQLAlchemy engine whose Session query returns *row*."""
    from src.models import ResearchRunLog

    engine = MagicMock()

    if raise_exc:
        # Make Session(engine).__enter__() raise
        session_ctx = MagicMock()
        session_ctx.__enter__ = MagicMock(side_effect=RuntimeError("DB error"))
        session_ctx.__exit__ = MagicMock(return_value=False)
        engine.__class__ = type(engine)  # keep it a MagicMock
        with patch("src.ui.executive_reports.Session", return_value=session_ctx):
            return engine  # caller must use the patch context

    row = None if no_row else MagicMock(spec=ResearchRunLog)
    if row is not None:
        row.run_id = run_id
        row.strategy_report = (
            json.dumps(strategy_report) if strategy_report is not None else None
        )
        row.confidence_scores = (
            json.dumps(confidence_scores) if confidence_scores is not None else None
        )

    session_mock = MagicMock()
    session_mock.query.return_value.filter.return_value.first.return_value = row
    session_ctx = MagicMock()
    session_ctx.__enter__ = MagicMock(return_value=session_mock)
    session_ctx.__exit__ = MagicMock(return_value=False)

    return engine, session_ctx


# ---------------------------------------------------------------------------
# (a) Checkpoint state present → used directly
# ---------------------------------------------------------------------------

def test_checkpoint_state_present_returns_checkpoint_source():
    graph = _make_graph_with_state(
        strategy_report=SAMPLE_REPORT,
        confidence_scores=SAMPLE_CONFIDENCE,
        intelligence_findings=SAMPLE_FINDINGS,
        critic_feedback=SAMPLE_CRITIC,
    )
    engine = MagicMock()  # should NOT be consulted

    result = _load_report_data("run-abc-123", graph, engine)

    assert result["source"] == "checkpoint"
    assert result["report"] == SAMPLE_REPORT
    assert result["confidence"] == SAMPLE_CONFIDENCE
    assert result["findings"] == SAMPLE_FINDINGS
    assert result["critic"] == SAMPLE_CRITIC
    assert result["error"] is None
    # Engine should never have been used
    engine.connect.assert_not_called()


def test_checkpoint_state_present_metadata_returned():
    meta = {"langsmith_run_url": "https://smith.langchain.com/traces/xyz"}
    graph = _make_graph_with_state(
        strategy_report=SAMPLE_REPORT,
        execution_metadata=meta,
    )
    engine = MagicMock()

    result = _load_report_data("run-meta-456", graph, engine)

    assert result["source"] == "checkpoint"
    assert result["metadata"]["langsmith_run_url"] == meta["langsmith_run_url"]


# ---------------------------------------------------------------------------
# (b) Checkpoint state empty → ResearchRunLog fallback used
# ---------------------------------------------------------------------------

def test_empty_checkpoint_falls_back_to_db():
    graph = _make_graph_with_state(strategy_report=None)  # empty state
    engine, session_ctx = _make_engine_with_row(
        "run-empty-001",
        strategy_report=SAMPLE_REPORT,
        confidence_scores=SAMPLE_CONFIDENCE,
    )

    with patch("src.ui.executive_reports.Session", return_value=session_ctx):
        result = _load_report_data("run-empty-001", graph, engine)

    assert result["source"] == "db_fallback"
    assert result["report"] == SAMPLE_REPORT
    assert result["confidence"] == SAMPLE_CONFIDENCE
    # checkpoint-only fields must be empty dicts
    assert result["findings"] == {}
    assert result["critic"] == {}
    assert result["metadata"] == {}
    assert result["error"] is None


def test_checkpoint_exception_falls_back_to_db():
    graph = _make_graph_with_state(raise_exc=True)
    engine, session_ctx = _make_engine_with_row(
        "run-exc-001",
        strategy_report=SAMPLE_REPORT,
        confidence_scores=SAMPLE_CONFIDENCE,
    )

    with patch("src.ui.executive_reports.Session", return_value=session_ctx):
        result = _load_report_data("run-exc-001", graph, engine)

    assert result["source"] == "db_fallback"
    assert result["report"] == SAMPLE_REPORT
    assert result["error"] is None


# ---------------------------------------------------------------------------
# (c) Both checkpoint and DB empty → graceful unavailable result, no exception
# ---------------------------------------------------------------------------

def test_both_sources_empty_returns_unavailable_no_exception():
    graph = _make_graph_with_state(strategy_report=None)
    engine, session_ctx = _make_engine_with_row(
        "run-both-empty",
        strategy_report=None,
        confidence_scores=None,
    )

    with patch("src.ui.executive_reports.Session", return_value=session_ctx):
        result = _load_report_data("run-both-empty", graph, engine)

    assert result["source"] == "unavailable"
    assert result["error"] is not None
    assert isinstance(result["error"], str)
    # Must not raise — function returns normally
    assert result["report"] == {}
    assert result["confidence"] == {}


def test_db_row_missing_returns_unavailable():
    graph = _make_graph_with_state(strategy_report=None)
    engine, session_ctx = _make_engine_with_row("run-no-row", no_row=True)

    with patch("src.ui.executive_reports.Session", return_value=session_ctx):
        result = _load_report_data("run-no-row", graph, engine)

    assert result["source"] == "unavailable"
    assert "No ResearchRunLog row found" in result["error"]


# ---------------------------------------------------------------------------
# (d) DB fallback raises exception → unavailable with descriptive error
# ---------------------------------------------------------------------------

def test_db_fallback_exception_returns_unavailable_with_message():
    graph = _make_graph_with_state(strategy_report=None)

    # Patch Session to raise on __enter__
    bad_session_ctx = MagicMock()
    bad_session_ctx.__enter__ = MagicMock(side_effect=RuntimeError("connection refused"))
    bad_session_ctx.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()

    with patch("src.ui.executive_reports.Session", return_value=bad_session_ctx):
        result = _load_report_data("run-db-fail", graph, engine)

    assert result["source"] == "unavailable"
    assert "fallback" in result["error"].lower() or "unavailable" in result["error"].lower()
    assert result["report"] == {}


# ---------------------------------------------------------------------------
# (e) Malformed JSON in strategy_report → report={}, but confidence parsed OK
# ---------------------------------------------------------------------------

def test_malformed_strategy_report_json_does_not_crash():
    graph = _make_graph_with_state(strategy_report=None)

    row = MagicMock()
    row.strategy_report = "NOT_VALID_JSON{{{"
    row.confidence_scores = json.dumps(SAMPLE_CONFIDENCE)

    session_mock = MagicMock()
    session_mock.query.return_value.filter.return_value.first.return_value = row
    session_ctx = MagicMock()
    session_ctx.__enter__ = MagicMock(return_value=session_mock)
    session_ctx.__exit__ = MagicMock(return_value=False)

    engine = MagicMock()
    with patch("src.ui.executive_reports.Session", return_value=session_ctx):
        result = _load_report_data("run-bad-json", graph, engine)

    # confidence is valid so we get db_fallback, not unavailable
    assert result["source"] == "db_fallback"
    assert result["report"] == {}
    assert result["confidence"] == SAMPLE_CONFIDENCE


# ---------------------------------------------------------------------------
# (f) Return schema always complete (all 7 keys present for every scenario)
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {"source", "report", "confidence", "metadata", "findings", "critic", "error"}


@pytest.mark.parametrize("scenario", ["checkpoint", "db_fallback", "unavailable"])
def test_return_schema_always_complete(scenario):
    if scenario == "checkpoint":
        graph = _make_graph_with_state(strategy_report=SAMPLE_REPORT)
        engine = MagicMock()
        result = _load_report_data("r1", graph, engine)

    elif scenario == "db_fallback":
        graph = _make_graph_with_state(strategy_report=None)
        engine, session_ctx = _make_engine_with_row(
            "r2", strategy_report=SAMPLE_REPORT, confidence_scores=SAMPLE_CONFIDENCE
        )
        with patch("src.ui.executive_reports.Session", return_value=session_ctx):
            result = _load_report_data("r2", graph, engine)

    else:  # unavailable
        graph = _make_graph_with_state(strategy_report=None)
        engine, session_ctx = _make_engine_with_row("r3", no_row=True)
        with patch("src.ui.executive_reports.Session", return_value=session_ctx):
            result = _load_report_data("r3", graph, engine)

    assert REQUIRED_KEYS == set(result.keys()), (
        f"Return schema incomplete for scenario={scenario!r}: got {set(result.keys())}"
    )
