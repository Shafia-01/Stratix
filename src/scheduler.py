"""
Keylytics keyword monitoring scheduler.

Uses APScheduler with SQLAlchemy job store to persist monitoring jobs
across restarts. Each job runs the full LangGraph pipeline in auto-approve
mode (HITL bypassed by pre-populating human_feedback={"approved": True}).

Usage:
    scheduler = KeylyticsScheduler(graph_fn=get_compiled_graph)
    scheduler.start()
    job_id = scheduler.add_monitoring_job("content marketing", interval_hours=12)
    scheduler.shutdown()
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Callable, List, Optional

from src.logger_config import get_logger
from src.schemas import MonitoringJob

logger = get_logger(__name__)

# Lazy APScheduler import so the module is still importable if apscheduler
# is not yet installed (will fail at runtime, not import time).
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.executors.pool import ThreadPoolExecutor
    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed — monitoring scheduler unavailable. "
                   "Run: pip install apscheduler>=3.10.0")


class KeylyticsScheduler:
    """
    Background scheduler for recurring keyword research jobs.

    graph_fn should be a callable returning the compiled LangGraph instance.
    The scheduler is initialised lazily; call start() before use.
    """

    def __init__(self, graph_fn: Callable) -> None:
        self._graph_fn = graph_fn
        self._scheduler: Optional[object] = None
        self._started = False

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Initialise and start the APScheduler background scheduler."""
        if not _APSCHEDULER_AVAILABLE:
            logger.error("Cannot start scheduler — APScheduler not installed.")
            return

        import os
        db_path = os.getenv("KEYLYTICS_DB_PATH", "keylytics.db")

        jobstores = {
            "default": SQLAlchemyJobStore(url=f"sqlite:///{db_path}"),
        }
        executors = {
            "default": ThreadPoolExecutor(max_workers=3),
        }
        job_defaults = {
            "coalesce": True,   # Merge missed executions into a single run
            "max_instances": 1,  # Only one instance of each job at a time
        }

        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
        )
        self._scheduler.start()
        self._started = True
        logger.info("KeylyticsScheduler started with SQLAlchemy job store.")

    def shutdown(self) -> None:
        """Shutdown the scheduler gracefully."""
        if self._scheduler and self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("KeylyticsScheduler stopped.")

    # ── Job management ─────────────────────────────────────────────────────

    def add_monitoring_job(
        self,
        seed_keyword: str,
        interval_hours: int = 24,
    ) -> str:
        """
        Schedule a recurring research job for a keyword.

        Returns:
            job_id (str) — use this to remove or query the job.
        """
        if not self._started or not self._scheduler:
            raise RuntimeError("Scheduler is not running. Call start() first.")

        job_id = f"monitor_{uuid.uuid4().hex[:12]}"

        self._scheduler.add_job(
            func=self._run_research_job,
            trigger="interval",
            hours=interval_hours,
            id=job_id,
            name=f"keylytics-monitor:{seed_keyword}",
            args=[seed_keyword, job_id],
            replace_existing=False,
        )

        # Persist to monitoring_jobs table
        self._upsert_job_record(job_id, seed_keyword, interval_hours, "active")
        logger.info(
            f"Monitoring job added: id={job_id}, keyword={seed_keyword!r}, "
            f"interval={interval_hours}h"
        )
        return job_id

    def remove_monitoring_job(self, job_id: str) -> bool:
        """
        Remove a monitoring job by ID.

        Returns:
            True if removed, False if not found.
        """
        if not self._started or not self._scheduler:
            return False

        try:
            self._scheduler.remove_job(job_id)
            self._delete_job_record(job_id)
            logger.info(f"Monitoring job removed: id={job_id}")
            return True
        except Exception as e:
            logger.warning(f"Could not remove job {job_id}: {e}")
            return False

    def list_jobs(self) -> List[MonitoringJob]:
        """Return all persisted monitoring jobs from the DB."""
        try:
            from src.db_client import connect_db
            from src.models import MonitoringJobModel
            from sqlalchemy.orm import Session

            engine = connect_db()
            with Session(engine) as session:
                rows = session.query(MonitoringJobModel).all()
                return [
                    MonitoringJob(
                        job_id=r.job_id,
                        seed_keyword=r.seed_keyword,
                        interval_hours=r.interval_hours,
                        last_run=r.last_run,
                        next_run=self._get_next_run(r.job_id),
                        status=r.status,
                    )
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"list_jobs failed: {e}", exc_info=True)
            return []

    # ── Internal helpers ───────────────────────────────────────────────────

    def _get_next_run(self, job_id: str) -> Optional[datetime]:
        """Get the next scheduled run time from APScheduler."""
        if not self._scheduler:
            return None
        try:
            job = self._scheduler.get_job(job_id)
            if job and job.next_run_time:
                return job.next_run_time
        except Exception:
            pass
        return None

    def _run_research_job(self, seed_keyword: str, job_id: str) -> None:
        """
        Execute the full LangGraph pipeline in auto-approve mode.
        HITL is bypassed: human_feedback is pre-populated with {"approved": True}.
        """
        run_id = str(uuid.uuid4())
        logger.info(f"Scheduler job started: job_id={job_id}, seed={seed_keyword!r}, run_id={run_id}")

        # Record run start
        self._log_run_start(run_id, seed_keyword)
        self._update_job_last_run(job_id)

        try:
            from src.graph.tracing import build_initial_metadata, get_run_config

            graph = self._graph_fn()
            config = get_run_config(seed_keyword, run_id)

            initial_state = {
                "seed_keyword": seed_keyword,
                "status": "pending",
                "awaiting_human": False,
                "messages": [],
                "errors": [],
                "execution_metadata": build_initial_metadata(run_id),
                # Auto-approve the plan — no HITL for scheduled runs
                "human_feedback": {"approved": True},
            }

            # Phase 1 invoke: runs through planner → interrupt → auto-approves
            result = graph.invoke(initial_state, config)
            current_state = graph.get_state(config)
            state_vals = current_state.values if current_state else result

            # If still awaiting approval after first run (planner interrupt),
            # resume with auto-approval
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
                current_state = graph.get_state(config)
                state_vals = current_state.values if current_state else result
                resumes += 1

            final_status = state_vals.get("status", "unknown")
            strategy_report = state_vals.get("strategy_report")
            confidence_scores = state_vals.get("confidence_scores")

            # Compute report diff if a previous run exists
            if strategy_report:
                self._compute_and_save_diff(
                    seed_keyword=seed_keyword,
                    curr_run_id=run_id,
                    curr_report=strategy_report,
                    curr_confidence=confidence_scores,
                )

            self._log_run_complete(run_id, final_status, strategy_report, confidence_scores)
            logger.info(f"Scheduler job completed: job_id={job_id}, status={final_status}")

        except Exception as e:
            logger.error(f"Scheduler job failed: job_id={job_id}, error={e}", exc_info=True)
            self._mark_job_failed(job_id)
            self._log_run_complete(run_id, "failed", None, None)

    def _compute_and_save_diff(
        self,
        seed_keyword: str,
        curr_run_id: str,
        curr_report: dict,
        curr_confidence: Optional[dict],
    ) -> None:
        """Fetch the previous run's report and compute + save a diff."""
        try:
            from src.db_client import connect_db
            from src.models import ResearchRunLog
            from src.report_diff import compute_report_diff, save_report_diff
            from sqlalchemy.orm import Session

            engine = connect_db()
            with Session(engine) as session:
                prev_log = (
                    session.query(ResearchRunLog)
                    .filter(
                        ResearchRunLog.seed_keyword == seed_keyword,
                        ResearchRunLog.run_id != curr_run_id,
                        ResearchRunLog.status == "completed",
                        ResearchRunLog.strategy_report.isnot(None),
                    )
                    .order_by(ResearchRunLog.completed_at.desc())
                    .first()
                )
                if not prev_log:
                    logger.info(f"No previous completed run for {seed_keyword!r} — skipping diff.")
                    return

                prev_report = json.loads(prev_log.strategy_report)
                prev_confidence = (
                    json.loads(prev_log.confidence_scores)
                    if prev_log.confidence_scores
                    else {}
                )

            diff = compute_report_diff(prev_report, curr_report, prev_confidence, curr_confidence)
            save_report_diff(diff, prev_run_id=prev_log.run_id, curr_run_id=curr_run_id)

        except Exception as e:
            logger.warning(f"Report diff computation failed (non-fatal): {e}")

    # ── DB helpers ─────────────────────────────────────────────────────────

    def _upsert_job_record(
        self,
        job_id: str,
        seed_keyword: str,
        interval_hours: int,
        status: str,
    ) -> None:
        try:
            from src.db_client import connect_db
            from src.models import MonitoringJobModel
            from sqlalchemy.orm import Session

            engine = connect_db()
            with Session(engine) as session:
                row = session.query(MonitoringJobModel).filter(
                    MonitoringJobModel.job_id == job_id
                ).first()
                if not row:
                    row = MonitoringJobModel(job_id=job_id)
                    session.add(row)
                row.seed_keyword = seed_keyword
                row.interval_hours = interval_hours
                row.status = status
                session.commit()
        except Exception as e:
            logger.error(f"_upsert_job_record failed: {e}", exc_info=True)

    def _delete_job_record(self, job_id: str) -> None:
        try:
            from src.db_client import connect_db
            from src.models import MonitoringJobModel
            from sqlalchemy.orm import Session

            engine = connect_db()
            with Session(engine) as session:
                session.query(MonitoringJobModel).filter(
                    MonitoringJobModel.job_id == job_id
                ).delete()
                session.commit()
        except Exception as e:
            logger.error(f"_delete_job_record failed: {e}", exc_info=True)

    def _update_job_last_run(self, job_id: str) -> None:
        try:
            from src.db_client import connect_db
            from src.models import MonitoringJobModel
            from sqlalchemy.orm import Session

            engine = connect_db()
            with Session(engine) as session:
                row = session.query(MonitoringJobModel).filter(
                    MonitoringJobModel.job_id == job_id
                ).first()
                if row:
                    row.last_run = datetime.now(timezone.utc)
                    session.commit()
        except Exception as e:
            logger.error(f"_update_job_last_run failed: {e}", exc_info=True)

    def _mark_job_failed(self, job_id: str) -> None:
        try:
            from src.db_client import connect_db
            from src.models import MonitoringJobModel
            from sqlalchemy.orm import Session

            engine = connect_db()
            with Session(engine) as session:
                row = session.query(MonitoringJobModel).filter(
                    MonitoringJobModel.job_id == job_id
                ).first()
                if row:
                    row.status = "failed"
                    session.commit()
        except Exception as e:
            logger.error(f"_mark_job_failed failed: {e}", exc_info=True)

    def _log_run_start(self, run_id: str, seed_keyword: str) -> None:
        try:
            from src.db_client import connect_db
            from src.models import ResearchRunLog
            from sqlalchemy.orm import Session

            engine = connect_db()
            with Session(engine) as session:
                row = ResearchRunLog(
                    run_id=run_id,
                    seed_keyword=seed_keyword,
                    triggered_by="scheduler",
                    status="pending",
                )
                session.add(row)
                session.commit()
        except Exception as e:
            logger.error(f"_log_run_start failed: {e}", exc_info=True)

    def _log_run_complete(
        self,
        run_id: str,
        status: str,
        strategy_report: Optional[dict],
        confidence_scores: Optional[dict],
    ) -> None:
        try:
            from src.db_client import connect_db
            from src.models import ResearchRunLog
            from sqlalchemy.orm import Session

            engine = connect_db()
            with Session(engine) as session:
                row = session.query(ResearchRunLog).filter(
                    ResearchRunLog.run_id == run_id
                ).first()
                if not row:
                    row = ResearchRunLog(run_id=run_id, seed_keyword="unknown")
                    session.add(row)
                row.status = status
                row.completed_at = datetime.now(timezone.utc)
                if strategy_report:
                    row.strategy_report = json.dumps(strategy_report, default=str)
                if confidence_scores:
                    row.confidence_scores = json.dumps(confidence_scores)
                session.commit()
        except Exception as e:
            logger.error(f"_log_run_complete failed: {e}", exc_info=True)
