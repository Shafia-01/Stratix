from typing import List, Any
from pydantic import BaseModel, Field
from src.trend_forecaster import analyze_trend_forecasting
from src.schemas import TrendForecastResult
from src.exceptions import KeylyticsAPIError

class TrendForecastInput(BaseModel):
    keywords: List[str] = Field(..., description="List of keywords to analyze and forecast trends for")

def run(input: TrendForecastInput) -> TrendForecastResult:
    """Execute trend forecasting tool."""
    try:
        # Convert List[str] input to expected keywords_data structure
        keywords_data = [{"keyword": kw} for kw in input.keywords]
        res = analyze_trend_forecasting(keywords_data)
        if isinstance(res, dict) and "error" in res:
            raise KeylyticsAPIError(res["error"])
        
        # Format insights list if needed (it contains dicts, but let's extract summaries/titles)
        insights_list = []
        for insight in res.get("insights", []):
            if isinstance(insight, dict):
                insights_list.append(f"{insight.get('title')}: {insight.get('description')}")
            else:
                insights_list.append(str(insight))
                
        return TrendForecastResult(
            forecasts=res.get("forecasts", {}),
            seasonal_analysis=res.get("seasonal_analysis", {}),
            insights=insights_list,
            summary=res.get("summary", "")
        )
    except Exception as e:
        raise KeylyticsAPIError(f"Trend forecast tool failed: {e}") from e
