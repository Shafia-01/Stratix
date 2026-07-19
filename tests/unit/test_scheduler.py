import pytest
from unittest.mock import MagicMock, patch
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
        assert job.status == "failed"
        mock_apsched.pause_job.assert_called_once_with(job_id)
