from fastapi import APIRouter, HTTPException
from src.tools.serp_analysis_tool import run as run_serp_analysis, SerpAnalysisInput
from src.schemas import SerpAnalysisResult
from src.exceptions import KeylyticsAPIError, KeylyticsDataError
from src.security_utils import redact_api_keys
from src.logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/analyze", response_model=SerpAnalysisResult)
def analyze_serp(req: SerpAnalysisInput):
    logger.info(f"POST /api/v1/serp/analyze for keyword: '{req.keyword}'")
    try:
        return run_serp_analysis(req)
    except (KeylyticsAPIError, KeylyticsDataError) as e:
        redacted_msg = redact_api_keys(str(e))
        logger.error(f"API/Data error in analyze_serp: {redacted_msg}")
        raise HTTPException(status_code=502, detail=redacted_msg)
    except Exception as e:
        redacted_msg = redact_api_keys(str(e))
        logger.error(f"Unexpected error in analyze_serp: {redacted_msg}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
