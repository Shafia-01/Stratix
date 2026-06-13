"""
Intelligence routes for Keylytics API.

All routes are async and wrap synchronous tool run() calls in a thread pool
to avoid blocking the event loop under concurrent load.

Routes (legacy sub-paths preserved for parity)
-----------------------------------------------
POST /intelligence/serp        → SerpAnalysisInput  → SerpAnalysisResult
POST /intelligence/competitors → CompetitorGapInput  → CompetitorGapResult
POST /intelligence/trends      → TrendForecastInput  → TrendForecastResult
POST /intelligence/clusters    → TopicClusterInput   → TopicClusterResult
POST /intelligence/intent      → IntentClassifierInput → IntentClassification

Legacy sub-path aliases (kept for backward compatibility during migration)
POST /intelligence/serp/analyze        (same handler, aliased)
POST /intelligence/competitors/gap     (same handler, aliased)
POST /intelligence/trends/forecast     (same handler, aliased)
POST /intelligence/clusters/topic      (same handler, aliased)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from src.tools.serp_analysis_tool import SerpAnalysisInput, run as run_serp
from src.tools.competitor_gap_tool import CompetitorGapInput, run as run_competitor_gap
from src.tools.trend_forecast_tool import TrendForecastInput, run as run_trend_forecast
from src.tools.topic_cluster_tool import TopicClusterInput, run as run_topic_cluster
from src.tools.intent_classifier_tool import IntentClassifierInput, run as run_intent_classifier
from src.schemas import (
    SerpAnalysisResult,
    CompetitorGapResult,
    TrendForecastResult,
    TopicClusterResult,
    IntentClassification,
)
from src.exceptions import KeylyticsAPIError, KeylyticsDataError
from src.security_utils import redact_api_keys
from src.logger_config import get_logger
from api.dependencies import get_db_session

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helper: unified error handling wrapper to avoid repetition
# ---------------------------------------------------------------------------
def _handle_tool_error(exc: Exception, route_name: str) -> HTTPException:
    msg = redact_api_keys(str(exc))
    if isinstance(exc, (KeylyticsAPIError, KeylyticsDataError)):
        logger.error(f"API/Data error in {route_name}: {msg}")
        return HTTPException(status_code=502, detail=msg)
    if isinstance(exc, ValidationError):
        logger.error(f"Validation error in {route_name}: {msg}")
        return HTTPException(status_code=422, detail=exc.errors())
    logger.error(f"Unexpected error in {route_name}: {msg}", exc_info=True)
    return HTTPException(status_code=500, detail="An unexpected error occurred.")


# ---------------------------------------------------------------------------
# SERP Analysis  (legacy: POST /api/v1/serp/analyze)
# ---------------------------------------------------------------------------
@router.post("/serp", response_model=SerpAnalysisResult)
@router.post("/serp/analyze", response_model=SerpAnalysisResult, include_in_schema=False)
async def analyze_serp(req: SerpAnalysisInput, _db=Depends(get_db_session)):
    """Analyze search engine results for snippet, PAA, ranking, and content gaps."""
    logger.info(f"POST /intelligence/serp — keyword='{req.keyword}'")
    try:
        return await run_in_threadpool(run_serp, req)
    except Exception as exc:
        raise _handle_tool_error(exc, "analyze_serp")


# ---------------------------------------------------------------------------
# Competitor Gap  (legacy: POST /api/v1/competitors/gap)
# ---------------------------------------------------------------------------
@router.post("/competitors", response_model=CompetitorGapResult)
@router.post("/competitors/gap", response_model=CompetitorGapResult, include_in_schema=False)
async def analyze_competitors(req: CompetitorGapInput, _db=Depends(get_db_session)):
    """Identify keyword gaps between your site and top competitors."""
    logger.info(f"POST /intelligence/competitors — seed='{req.seed_keyword}'")
    try:
        return await run_in_threadpool(run_competitor_gap, req)
    except Exception as exc:
        raise _handle_tool_error(exc, "analyze_competitors")


# ---------------------------------------------------------------------------
# Trend Forecast  (legacy: POST /api/v1/trends/forecast)
# ---------------------------------------------------------------------------
@router.post("/trends", response_model=TrendForecastResult)
@router.post("/trends/forecast", response_model=TrendForecastResult, include_in_schema=False)
async def forecast_trends(req: TrendForecastInput, _db=Depends(get_db_session)):
    """Forecast keyword trend trajectories and seasonal patterns."""
    logger.info(f"POST /intelligence/trends — keywords={req.keywords}")
    try:
        return await run_in_threadpool(run_trend_forecast, req)
    except Exception as exc:
        raise _handle_tool_error(exc, "forecast_trends")


# ---------------------------------------------------------------------------
# Topic Clustering  (legacy: POST /api/v1/clusters/topic)
# ---------------------------------------------------------------------------
@router.post("/clusters", response_model=TopicClusterResult)
@router.post("/clusters/topic", response_model=TopicClusterResult, include_in_schema=False)
async def cluster_topics(req: TopicClusterInput, _db=Depends(get_db_session)):
    """Cluster a keyword list into semantic topic groups."""
    logger.info("POST /intelligence/clusters")
    try:
        return await run_in_threadpool(run_topic_cluster, req)
    except Exception as exc:
        raise _handle_tool_error(exc, "cluster_topics")


# ---------------------------------------------------------------------------
# Intent Classification  (NEW — not in legacy routers)
# ---------------------------------------------------------------------------
@router.post("/intent", response_model=IntentClassification)
async def classify_intent(req: IntentClassifierInput, _db=Depends(get_db_session)):
    """Classify the search intent of a keyword (informational/commercial/transactional/navigational)."""
    logger.info(f"POST /intelligence/intent — keyword='{req.keyword}'")
    try:
        return await run_in_threadpool(run_intent_classifier, req)
    except Exception as exc:
        raise _handle_tool_error(exc, "classify_intent")
