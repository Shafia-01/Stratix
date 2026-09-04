"""
End-to-end integration test for the KeylyticsScheduler monitoring pipeline.

Tests:
 1. Create a monitoring job via KeylyticsScheduler.add_monitoring_job using
    the real APScheduler BackgroundScheduler (same pattern as test_scheduler.py).
 2. Force-execute _run_scheduled_research_job with the graph mocked to return a
    valid completed state.  Assert a ResearchRunLog row was created.
 3. Run a second time with different (higher-scoring) keyword opportunities in
    the mocked graph result, so that compute_report_diff produces a non-trivial
    ReportDiff (keywords appear/improve/decline between the two runs).
 4. Assert the ReportDiff is retrievable via get_latest_report_diff and contains
    at least one non-zero keyword delta.

Uses the existing tmp_db_path fixture from tests/conftest.py.
APScheduler is used exactly as in tests/unit/test_scheduler.py: a real
BackgroundScheduler is started, the job is added, and the scheduler is shut
down after the test — the job function itself is invoked directly (not via the
scheduler trigger interval) so the test is deterministic and fast.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.db_client import connect_db
from src.models import MonitoringJobModel, ResearchRunLog
from src.report_diff import (
    compute_report_diff,
    get_latest_report_diff,
    save_report_diff,
)
from src.scheduler import KeylyticsScheduler, _run_scheduled_research_job
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Helpers: minimal strategy reports with different keyword scores
# ---------------------------------------------------------------------------


def _make_state(seed: str, kw_scores: Dict[str, float], run_id: str) -> Dict[str, Any]:
    """
    Build a minimal final AgentState dict that _run_research_job would produce
    after a successful run, with the given keyword scores in strategy_report.
    """
    top_opps = []
    for kw, score in kw_scores.items():
        top_opps.append(
            {
                "seed": seed,
                "keyword": kw,
                "volume": 1000.0,
                "competition": 0.3,
                "cpc": 1.0,
                "trend": None,
                "score": score,
                "difficulty": "Medium",
                "intent": "Informational",
                "competitors": [],
                "data_source": "unavailable",
                "trend_data_source": "unavailable",
            }
        )

    strategy_report = {
        "seed_keyword": seed,
        "executive_summary": f"Analysis of {seed} — run {run_id}.",
        "top_opportunities": top_opps,
        "recommendations": [
            "Focus on low-competition keywords.",
            "Build topic clusters around seed keyword.",
            "Monitor competitor content gaps.",
            "Target voice-search friendly queries.",
            "Develop long-form cornerstone content.",
        ],
        "version": "phase3",
    }

    return {
        "seed_keyword": seed,
        "status": "completed",
        "strategy_report": strategy_report,
        "confidence_scores": {"keyword_research": 1.0},
        "intelligence_findings": {
            "seed_keyword": seed,
            "keyword_findings": [],
        },
        "errors": [],
        "execution_metadata": {
            "run_id": run_id,
            "start_ts": datetime.now(timezone.utc).isoformat(),
            "end_ts": datetime.now(timezone.utc).isoformat(),
            "total_tool_calls": 3,
            "tool_call_counts": {"keyword_research": 1},
            "planner_retries": 1,
            "strategy_retries": 1,
        },
        "messages": [],
        "awaiting_human": False,
        "human_feedback": None,
    }


# ---------------------------------------------------------------------------
# Fixture: real APScheduler with tmp_db_path (mirrors test_scheduler.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def scheduler_with_mock_graph(tmp_db_path):
    """
    Start a real KeylyticsScheduler backed by the tmp SQLite DB.
    Yields (scheduler, graph_mock) for the test to use.
    Tears down the scheduler after the test.
    """
    # Provide a mock graph function (will be replaced per-call in the test)
    mock_graph_fn = MagicMock()

    sched = KeylyticsScheduler(graph_fn=mock_graph_fn)
    sched.start()
    yield sched, mock_graph_fn
    sched.shutdown()


# ---------------------------------------------------------------------------
# E2E Test
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_monitoring_e2e_run_and_diff(tmp_db_path, scheduler_with_mock_graph):
    """
    Full monitoring E2E:
      1. Add a monitoring job via add_monitoring_job.
      2. Force-execute _run_scheduled_research_job (run 1) with graph mocked to
         return a completed state with keyword scores {A: 70, B: 50}.
      3. Assert a ResearchRunLog row was created with status="completed".
      4. Force-execute _run_scheduled_research_job (run 2) with graph mocked to
         return a completed state with keyword scores {A: 85, C: 60} so that:
           - keyword A improves (70 -> 85)
           - keyword B drops out
           - keyword C appears as new
      5. Assert a second ResearchRunLog row exists.
      6. Assert compute_report_diff between run1 and run2 is non-trivial
         (contains at least one delta != 0 or a new/dropped keyword).
      7. Assert get_latest_report_diff returns the stored diff.
    """
    sched, mock_graph_fn = scheduler_with_mock_graph

    seed_keyword = "monitoring coffee"

    # ── Step 1: Add monitoring job ──────────────────────────────────────────
    job_id = sched.add_monitoring_job(seed_keyword, interval_hours=24)
    assert job_id.startswith("monitor_")

    # Verify job record exists in DB
    engine = connect_db()
    with Session(engine) as session:
        job_row = (
            session.query(MonitoringJobModel)
            .filter(MonitoringJobModel.job_id == job_id)
            .first()
        )
    assert job_row is not None
    assert job_row.seed_keyword == seed_keyword
    assert job_row.status == "active"

    # ── Step 2: Force-execute run 1 ────────────────────────────────────────
    run_id_1 = str(uuid.uuid4())
    kw_scores_1 = {"organic coffee beans": 70.0, "best organic coffee": 50.0}
    state_1 = _make_state(seed_keyword, kw_scores_1, run_id_1)

    def _make_graph_mock(state_dict):
        """Returns a mock compiled graph that immediately returns state_dict."""
        mock_graph = MagicMock()
        mock_graph_state = MagicMock()
        mock_graph_state.values = state_dict
        mock_graph.invoke.return_value = state_dict
        mock_graph.get_state.return_value = mock_graph_state
        mock_graph.update_state.return_value = None
        return mock_graph

    graph_mock_1 = _make_graph_mock(state_1)
    mock_graph_fn.return_value = graph_mock_1

    with patch("src.graph.graph.get_compiled_graph", return_value=graph_mock_1):
        _run_scheduled_research_job(seed_keyword, job_id)

    # Assert run 1 log row created
    with Session(engine) as session:
        run_logs = (
            session.query(ResearchRunLog)
            .filter(ResearchRunLog.seed_keyword == seed_keyword)
            .order_by(ResearchRunLog.started_at.asc())
            .all()
        )
    assert len(run_logs) >= 1, "Expected at least one ResearchRunLog row after run 1."
    run1_log = run_logs[0]
    assert run1_log.status == "completed", (
        f"Run 1 log status expected 'completed', got {run1_log.status!r}"
    )
    assert run1_log.strategy_report is not None, (
        "Run 1 strategy_report must not be NULL."
    )

    # ── Step 3: Force-execute run 2 with different keyword scores ───────────
    run_id_2 = str(uuid.uuid4())
    kw_scores_2 = {
        "organic coffee beans": 85.0,  # A improved from 70 -> 85
        "organic coffee brewing": 60.0,  # C: new keyword
        # "best organic coffee" deliberately dropped
    }
    state_2 = _make_state(seed_keyword, kw_scores_2, run_id_2)

    graph_mock_2 = _make_graph_mock(state_2)
    mock_graph_fn.return_value = graph_mock_2

    with patch("src.graph.graph.get_compiled_graph", return_value=graph_mock_2):
        _run_scheduled_research_job(seed_keyword, job_id)

    # Assert run 2 log row created
    with Session(engine) as session:
        run_logs_after = (
            session.query(ResearchRunLog)
            .filter(ResearchRunLog.seed_keyword == seed_keyword)
            .order_by(ResearchRunLog.started_at.asc())
            .all()
        )
    assert len(run_logs_after) >= 2, (
        f"Expected at least 2 ResearchRunLog rows after run 2, got {len(run_logs_after)}."
    )

    run2_log = run_logs_after[-1]
    assert run2_log.status == "completed", (
        f"Run 2 log status expected 'completed', got {run2_log.status!r}"
    )
    assert run2_log.strategy_report is not None

    # ── Step 4: Compute report diff between run 1 and run 2 ─────────────────
    report_1 = json.loads(run1_log.strategy_report)
    report_2 = json.loads(run2_log.strategy_report)

    diff = compute_report_diff(
        prev=report_1,
        curr=report_2,
        prev_confidence={"keyword_research": 1.0},
        curr_confidence={"keyword_research": 1.0},
    )

    # Assert the diff is non-trivial: at least one keyword delta exists
    assert len(diff.keyword_deltas) > 0, (
        "Expected at least one keyword delta between run 1 and run 2."
    )

    # At least one delta should be non-zero (keyword A improved by 15 points)
    non_zero_deltas = [d for d in diff.keyword_deltas if d.delta != 0.0]
    assert len(non_zero_deltas) > 0, (
        "Expected at least one non-zero keyword delta. "
        f"keyword_deltas={diff.keyword_deltas}"
    )

    # Verify the improved keyword is tracked
    improved = [d for d in diff.keyword_deltas if d.direction == "improved"]
    new_kws = [d for d in diff.keyword_deltas if d.direction == "new"]
    dropped = [d for d in diff.keyword_deltas if d.direction == "dropped"]

    # "organic coffee beans" improved, "organic coffee brewing" is new,
    # "best organic coffee" dropped
    assert len(improved) >= 1 or len(new_kws) >= 1, (
        "Expected at least one 'improved' or 'new' keyword delta."
    )
    assert len(dropped) >= 1, (
        "Expected at least one 'dropped' keyword (best organic coffee disappeared)."
    )

    # ── Step 5: Persist the diff and retrieve via get_latest_report_diff ────
    save_report_diff(diff, prev_run_id=run1_log.run_id, curr_run_id=run2_log.run_id)

    retrieved = get_latest_report_diff(seed_keyword)
    assert retrieved is not None, (
        "get_latest_report_diff returned None after saving a diff."
    )
    assert retrieved.seed_keyword == seed_keyword
    assert len(retrieved.keyword_deltas) > 0, (
        "Retrieved ReportDiff has no keyword_deltas."
    )
