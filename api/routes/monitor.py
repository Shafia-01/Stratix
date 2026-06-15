"""
FastAPI routes for keyword monitoring job management.

POST   /monitor/add                    — Add a recurring monitoring job
DELETE /monitor/{job_id}               — Remove a monitoring job
GET    /monitor/jobs                   — List all active monitoring jobs
GET    /monitor/history/{seed_keyword} — Last 10 research runs for a keyword
GET    /monitor/diff/{seed_keyword}    — Latest report diff for a keyword
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.logger_config import get_logger
from src.schemas import MonitoringJob, ReportDiff

logger = get_logger(__name__)
router = APIRouter(prefix="/monitor", tags=["Monitoring"])


# ── Request models ────────────────────────────────────────────────────────

class AddMonitoringJobRequest(BaseModel):
    """Request body for adding a new monitoring job."""
    seed_keyword: str = Field(..., description="Keyword to monitor")
    interval_hours: int = Field(24, ge=1, le=168, description="Run interval in hours (1–168)")


class AddMonitoringJobResponse(BaseModel):
    """Response after successfully adding a monitoring job."""
    job_id: str
    seed_keyword: str
    interval_hours: int
    message: str


class HistoryEntry(BaseModel):
    """Summary of a single research run for a monitored keyword."""
    run_id: str
    seed_keyword: str
    triggered_by: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    has_report: bool = False


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/add", response_model=AddMonitoringJobResponse)
async def add_monitoring_job(
    body: AddMonitoringJobRequest,
    request: Request,
) -> AddMonitoringJobResponse:
    """
    Schedule a recurring research job for a seed keyword.
    The job runs in auto-approve mode (no HITL) on the given interval.
    """
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(
            status_code=503,
            detail="Monitoring scheduler is not running. Check API startup logs.",
        )
    try:
        job_id = scheduler.add_monitoring_job(
            seed_keyword=body.seed_keyword,
            interval_hours=body.interval_hours,
        )
        return AddMonitoringJobResponse(
            job_id=job_id,
            seed_keyword=body.seed_keyword,
            interval_hours=body.interval_hours,
            message=(
                f"Monitoring job '{job_id}' created. "
                f"Will run every {body.interval_hours}h for '{body.seed_keyword}'."
            ),
        )
    except Exception as e:
        logger.error(f"add_monitoring_job failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
async def remove_monitoring_job(job_id: str, request: Request) -> Dict[str, Any]:
    """Remove a monitoring job by its job_id."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not running.")
    removed = scheduler.remove_monitoring_job(job_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return {"removed": True, "job_id": job_id}


@router.get("/jobs", response_model=List[MonitoringJob])
async def list_monitoring_jobs(request: Request) -> List[MonitoringJob]:
    """List all active monitoring jobs with their status and schedule."""
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is None:
        # Return from DB even if scheduler not running
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
                        next_run=None,
                        status=r.status,
                    )
                    for r in rows
                ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return scheduler.list_jobs()


@router.get("/history/{seed_keyword}", response_model=List[HistoryEntry])
async def get_research_history(seed_keyword: str) -> List[HistoryEntry]:
    """Return the last 10 research runs for a monitored keyword."""
    try:
        from src.db_client import connect_db
        from src.models import ResearchRunLog
        from sqlalchemy.orm import Session

        engine = connect_db()
        with Session(engine) as session:
            rows = (
                session.query(ResearchRunLog)
                .filter(ResearchRunLog.seed_keyword == seed_keyword)
                .order_by(ResearchRunLog.started_at.desc())
                .limit(10)
                .all()
            )
            return [
                HistoryEntry(
                    run_id=r.run_id,
                    seed_keyword=r.seed_keyword,
                    triggered_by=r.triggered_by,
                    status=r.status,
                    started_at=r.started_at.isoformat() if r.started_at else None,
                    completed_at=r.completed_at.isoformat() if r.completed_at else None,
                    has_report=bool(r.strategy_report),
                )
                for r in rows
            ]
    except Exception as e:
        logger.error(f"get_research_history failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diff/{seed_keyword}", response_model=Optional[ReportDiff])
async def get_report_diff(seed_keyword: str) -> Optional[ReportDiff]:
    """Return the latest computed report diff for a monitored keyword."""
    try:
        from src.report_diff import get_latest_report_diff

        diff = get_latest_report_diff(seed_keyword)
        if diff is None:
            raise HTTPException(
                status_code=404,
                detail=f"No report diff found for '{seed_keyword}'. Requires at least 2 completed runs.",
            )
        return diff
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_report_diff failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
