from fastapi import APIRouter, HTTPException
from src.tools.competitor_gap_tool import run as run_competitor_gap, CompetitorGapInput
from src.schemas import CompetitorGapResult
from src.exceptions import KeylyticsAPIError, KeylyticsDataError
from src.security_utils import redact_api_keys
from src.logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/gap", response_model=CompetitorGapResult)
def analyze_competitor_gap(req: CompetitorGapInput):
    logger.info(f"POST /api/v1/competitors/gap for seed: '{req.seed_keyword}'")
    try:
        return run_competitor_gap(req)
    except (KeylyticsAPIError, KeylyticsDataError) as e:
        redacted_msg = redact_api_keys(str(e))
        logger.error(f"API/Data error in analyze_competitor_gap: {redacted_msg}")
        raise HTTPException(status_code=502, detail=redacted_msg)
    except Exception as e:
        redacted_msg = redact_api_keys(str(e))
        logger.error(f"Unexpected error in analyze_competitor_gap: {redacted_msg}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
