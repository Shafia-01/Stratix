"""
Keyword routes for Keylytics API.

Routes
------
POST /keywords/research  → KeywordResearchInput → List[KeywordSuggestion]
GET  /keywords/history   → List[dict] (wraps fetch_past_results, limit query param)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from src.tools.keyword_research_tool import KeywordResearchInput, run as run_keyword_research
from src.schemas import KeywordSuggestion
from src.db_client import fetch_past_results
from src.exceptions import KeylyticsAPIError, KeylyticsDataError
from src.security_utils import redact_api_keys
from src.logger_config import get_logger
from api.dependencies import get_db_session

logger = get_logger(__name__)
router = APIRouter()


@router.post("/research", response_model=List[KeywordSuggestion])
async def research_keywords(req: KeywordResearchInput, _db=Depends(get_db_session)):
    """
    Discover related keywords for a seed term.
    Wraps the synchronous keyword_research_tool.run() in a thread pool
    so it does not block the event loop.
    """
    logger.info(f"POST /keywords/research — seed='{req.seed_keyword}' max={req.max_keywords}")
    try:
        return await run_in_threadpool(run_keyword_research, req)
    except (KeylyticsAPIError, KeylyticsDataError) as exc:
        msg = redact_api_keys(str(exc))
        logger.error(f"API/Data error in research_keywords: {msg}")
        raise HTTPException(status_code=502, detail=msg)
    except ValidationError as exc:
        logger.error(f"Validation error in research_keywords: {exc}")
        raise HTTPException(status_code=422, detail=exc.errors())
    except Exception as exc:
        msg = redact_api_keys(str(exc))
        logger.error(f"Unexpected error in research_keywords: {msg}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@router.get("/history")
async def keyword_history(
    limit: int = Query(50, ge=1, le=500, description="Max rows to return"),
    _db=Depends(get_db_session),
):
    """
    Return recent keyword research results from the database.
    Wraps the synchronous fetch_past_results() in a thread pool.
    """
    logger.info(f"GET /keywords/history — limit={limit}")
    try:
        df = await run_in_threadpool(fetch_past_results, limit)
        return df.to_dict(orient="records")
    except Exception as exc:
        msg = redact_api_keys(str(exc))
        logger.error(f"Unexpected error in keyword_history: {msg}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
