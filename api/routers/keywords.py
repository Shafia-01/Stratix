from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel, Field
from src.agent import run_agent
from src.lightweight_agent import run_lightweight_agent
from src.schemas import KeywordFinding
from src.exceptions import KeylyticsAPIError, KeylyticsDataError
from src.security_utils import redact_api_keys
from src.logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

class KeywordResearchRequest(BaseModel):
    seed_keyword: str = Field(..., description="Seed keyword to generate suggestions for")
    max_keywords: int = Field(50, description="Maximum number of keywords to return")

@router.post("/research", response_model=List[KeywordFinding])
def research_keywords(req: KeywordResearchRequest):
    logger.info(f"POST /api/v1/keywords/research for seed: '{req.seed_keyword}'")
    try:
        if req.max_keywords <= 5:
            results = run_lightweight_agent(req.seed_keyword, req.max_keywords)
        else:
            results = run_agent(req.seed_keyword, req.max_keywords)
        return results
    except (KeylyticsAPIError, KeylyticsDataError) as e:
        redacted_msg = redact_api_keys(str(e))
        logger.error(f"API/Data error in research_keywords: {redacted_msg}")
        raise HTTPException(status_code=502, detail=redacted_msg)
    except Exception as e:
        redacted_msg = redact_api_keys(str(e))
        logger.error(f"Unexpected error in research_keywords: {redacted_msg}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
