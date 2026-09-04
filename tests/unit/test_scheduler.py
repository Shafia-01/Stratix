import pytest
from unittest.mock import MagicMock
from src.scheduler import KeylyticsScheduler
from src.db_client import connect_db
from src.models import MonitoringJobModel
from sqlalchemy.orm import Session

@pytest.mark.unit
def test_scheduler_circuit_breaker(tmp_db_path, monkeypatch):
    def mock_graph_fn():
        raise Exception("Agent execution failure")

    scheduler = KeylyticsScheduler(graph_fn=mock_graph_fn)

    mock_apsched = MagicMock()
    scheduler._scheduler = mock_apsched
    scheduler._started = True

    job_id = "monitor_test_cb"
    scheduler._upsert_job_record(job_id, "coffee", 24, "active")

    # 1st failure
    scheduler._run_research_job("coffee", job_id)
    engine = connect_db()
    with Session(engine) as session:
        job = session.query(MonitoringJobModel).filter(MonitoringJobModel.job_id == job_id).first()
        assert job.consecutive_failures == 1
        assert job.status == "active"

    # 2nd failure
    scheduler._run_research_job("coffee", job_id)
    with Session(engine) as session:
        job = session.query(MonitoringJobModel).filter(MonitoringJobModel.job_id == job_id).first()
        assert job.consecutive_failures == 2
        assert job.status == "active"
        mock_apsched.pause_job.assert_not_called()

    # 3rd failure - circuit breaker triggers
    scheduler._run_research_job("coffee", job_id)
    with Session(engine) as session:
        job = session.query(MonitoringJobModel).filter(MonitoringJobModel.job_id == job_id).first()
        assert job.consecutive_failures == 3
        assert job.status == "paused_due_to_failures"
        mock_apsched.pause_job.assert_called_once_with(job_id)


@pytest.mark.unit
def test_resume_monitoring_job(tmp_db_path):
    scheduler = KeylyticsScheduler(graph_fn=MagicMock())
    mock_apsched = MagicMock()
    scheduler._scheduler = mock_apsched
    scheduler._started = True

    job_id = "monitor_test_resume"
    # Create job in DB with consecutive_failures=3 and status="paused_due_to_failures"
    scheduler._upsert_job_record(job_id, "coffee", 24, "paused_due_to_failures")
    engine = connect_db()
    with Session(engine) as session:
        job = session.query(MonitoringJobModel).filter(MonitoringJobModel.job_id == job_id).first()
        job.consecutive_failures = 3
        session.commit()

    # Resume the job
    resumed = scheduler.resume_monitoring_job(job_id)
    assert resumed is True
    mock_apsched.resume_job.assert_called_once_with(job_id)

    # Verify status and consecutive_failures are reset
    with Session(engine) as session:
        job = session.query(MonitoringJobModel).filter(MonitoringJobModel.job_id == job_id).first()
        assert job.consecutive_failures == 0
        assert job.status == "active"


@pytest.mark.unit
def test_dispatch_time_circuit_breaker_skips_paused_job(tmp_db_path, monkeypatch):
    """Verify _run_scheduled_research_job no-ops when job is paused_due_to_failures.

    This tests the authoritative enforcement mechanism: the DB-status check
    at the top of the module-level dispatch function must:
    1. Not create any ResearchRunLog entry (a skip is not a run).
    2. Never invoke the graph function.

    This mirrors the production APScheduler path where the throwaway
    KeylyticsScheduler has self._scheduler = None and cannot call
    pause_job() — relying solely on the DB gate to stop execution.
    """
    from unittest.mock import patch
    from src.scheduler import _run_scheduled_research_job
    from src.models import ResearchRunLog

    job_id = "monitor_test_dispatch_gate"
    seed_keyword = "iced coffee"

    # Set up a job record already in paused_due_to_failures state
    # (simulates a job that hit 3 consecutive failures in a prior run)
    dummy_scheduler = KeylyticsScheduler(graph_fn=MagicMock())
    dummy_scheduler._upsert_job_record(job_id, seed_keyword, 24, "paused_due_to_failures")

    engine = connect_db()

    # Snapshot the ResearchRunLog count before calling the dispatch function
    with Session(engine) as session:
        run_count_before = session.query(ResearchRunLog).count()

    # Patch get_compiled_graph so we can assert it is never called
    with patch("src.graph.graph.get_compiled_graph") as mock_get_graph:
        _run_scheduled_research_job(seed_keyword, job_id)

    # Assert: no ResearchRunLog row was created
    with Session(engine) as session:
        run_count_after = session.query(ResearchRunLog).count()
    assert run_count_after == run_count_before, (
        f"Expected no ResearchRunLog entries to be created for a paused job, "
        f"but count went from {run_count_before} to {run_count_after}"
    )

    # Assert: the graph function was never invoked
    mock_get_graph.assert_not_called()
