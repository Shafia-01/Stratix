"""
Trend forecasting tool for Keylytics.

Input:  TrendForecastInput — list of keyword strings.
Output: TrendForecastResult — fully typed with ForecastEntry and SeasonalAnalysisEntry,
        no Any or Dict[str, Any] in the result.
"""

from typing import List
from pydantic import BaseModel, Field
from src.trend_forecaster import analyze_trend_forecasting
from src.schemas import (
    TrendForecastResult,
    ForecastEntry,
    ForecastPoint,
    SeasonalAnalysisEntry,
)
from src.exceptions import KeylyticsAPIError


class TrendForecastInput(BaseModel):
    keywords: List[str] = Field(..., description="List of keywords to analyze and forecast trends for")


def run(input: TrendForecastInput) -> TrendForecastResult:
    """Execute trend forecasting tool and return typed TrendForecastResult."""
    try:
        # Convert List[str] input to the dict format expected by analyze_trend_forecasting
        keywords_data = [{"keyword": kw} for kw in input.keywords]
        res = analyze_trend_forecasting(keywords_data)
        if isinstance(res, dict) and "error" in res:
            raise KeylyticsAPIError(res["error"])

        # --- Build typed ForecastEntry models ---
        typed_forecasts: dict[str, ForecastEntry] = {}
        for kw, raw_fc in res.get("forecasts", {}).items():
            raw_points = raw_fc.get("forecast_scores", [])
            typed_points = [
                ForecastPoint(
                    month=pt.get("month", 0),
                    score=float(pt.get("score", 0.0)),
                    confidence=float(pt.get("confidence", 0.0)),
                )
                for pt in raw_points
            ]
            typed_forecasts[kw] = ForecastEntry(
                forecast_scores=typed_points,
                predicted_growth=float(raw_fc.get("predicted_growth", 0.0)),
                trend_direction=raw_fc.get("trend_direction", "stable"),
                recommendation=raw_fc.get("recommendation", ""),
            )

        # --- Build typed SeasonalAnalysisEntry models ---
        typed_seasonal: dict[str, SeasonalAnalysisEntry] = {}
        for kw, raw_sa in res.get("seasonal_analysis", {}).items():
            typed_seasonal[kw] = SeasonalAnalysisEntry(
                peak_season=raw_sa.get("peak_season"),
                low_season=raw_sa.get("low_season"),
                seasonality_strength=float(raw_sa.get("seasonality_strength", 0.0)),
                growth_rate=float(raw_sa["growth_rate"]) if raw_sa.get("growth_rate") is not None else None,
                recommendation=raw_sa.get("recommendation"),
            )

        # --- Format insights list ---
        insights_list: List[str] = []
        for insight in res.get("insights", []):
            if isinstance(insight, dict):
                insights_list.append(f"{insight.get('title', '')}: {insight.get('description', '')}")
            else:
                insights_list.append(str(insight))

        return TrendForecastResult(
            forecasts=typed_forecasts,
            seasonal_analysis=typed_seasonal,
            insights=insights_list,
            summary=res.get("summary", ""),
        )
    except KeylyticsAPIError:
        raise
    except Exception as exc:
        raise KeylyticsAPIError(f"Trend forecast tool failed: {exc}") from exc
