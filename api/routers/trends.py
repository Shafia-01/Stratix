from fastapi import APIRouter, HTTPException
from src.tools.trend_forecast_tool import run as run_trend_forecast, TrendForecastInput
from src.schemas import TrendForecastResult
from src.exceptions import KeylyticsAPIError, KeylyticsDataError
from src.security_utils import redact_api_keys
from src.logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/forecast", response_model=TrendForecastResult)
def forecast_trends(req: TrendForecastInput):
    logger.info(f"POST /api/v1/trends/forecast for keywords: '{req.keywords}'")
    try:
        return run_trend_forecast(req)
    except (KeylyticsAPIError, KeylyticsDataError) as e:
        redacted_msg = redact_api_keys(str(e))
        logger.error(f"API/Data error in forecast_trends: {redacted_msg}")
        raise HTTPException(status_code=502, detail=redacted_msg)
    except Exception as e:
        redacted_msg = redact_api_keys(str(e))
        logger.error(f"Unexpected error in forecast_trends: {redacted_msg}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
