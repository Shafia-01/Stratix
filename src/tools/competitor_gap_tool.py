"""
Competitor gap analysis tool for Keylytics.

Input:  CompetitorGapInput — seed keyword + top_competitors count.
Output: CompetitorGapResult — fully typed with List[CompetitorOpportunity],
        no Dict[str, Any] in the opportunities field.
"""

from typing import List
from pydantic import BaseModel, Field
from src.competitor_gap_analyzer import analyze_competitor_keyword_gap
from src.schemas import CompetitorGapResult, CompetitorEntry, CompetitorOpportunity
from src.exceptions import KeylyticsAPIError


class CompetitorGapInput(BaseModel):
    seed_keyword: str = Field(..., description="Seed keyword to analyze competitor gap for")
    top_competitors: int = Field(3, description="Number of top competitors to analyze")


def run(input: CompetitorGapInput) -> CompetitorGapResult:
    """Execute competitor keyword gap tool and return typed CompetitorGapResult."""
    try:
        res = analyze_competitor_keyword_gap(input.seed_keyword, input.top_competitors)
        if isinstance(res, dict) and "error" in res:
            raise KeylyticsAPIError(res["error"])

        # Build typed CompetitorEntry models
        competitors: List[CompetitorEntry] = [
            CompetitorEntry(
                domain=c.get("domain", ""),
                rank=c.get("rank", 0),
                title=c.get("title"),
                url=c.get("link"),
            )
            for c in res.get("competitors", [])
        ]

        # Build typed CompetitorOpportunity models
        opportunities: List[CompetitorOpportunity] = []
        for opp in res.get("opportunities", []):
            # Normalise traffic_potential to the allowed Literal values
            tp_raw = str(opp.get("traffic_potential", "medium")).lower()
            if tp_raw not in ("high", "medium", "low"):
                tp_raw = "medium"
            opportunities.append(
                CompetitorOpportunity(
                    keyword=opp.get("keyword", ""),
                    opportunity_type=opp.get("opportunity_type", "keyword_gap"),
                    gap_score=float(opp.get("gap_score", 0.0)),
                    traffic_potential=tp_raw,  # type: ignore[arg-type]
                    reasoning=opp.get("reasoning", ""),
                )
            )

        return CompetitorGapResult(
            competitors=competitors,
            opportunities=opportunities,
            summary=res.get("summary", ""),
        )
    except KeylyticsAPIError:
        raise
    except Exception as exc:
        raise KeylyticsAPIError(f"Competitor gap tool failed: {exc}") from exc
