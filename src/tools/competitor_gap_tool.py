from pydantic import BaseModel, Field
from src.competitor_gap_analyzer import analyze_competitor_keyword_gap
from src.schemas import CompetitorGapResult, CompetitorEntry
from src.exceptions import KeylyticsAPIError

class CompetitorGapInput(BaseModel):
    seed_keyword: str = Field(..., description="Seed keyword to analyze competitor gap for")
    top_competitors: int = Field(3, description="Number of top competitors to analyze")

def run(input: CompetitorGapInput) -> CompetitorGapResult:
    """Execute competitor keyword gap tool."""
    try:
        res = analyze_competitor_keyword_gap(input.seed_keyword, input.top_competitors)
        if isinstance(res, dict) and "error" in res:
            raise KeylyticsAPIError(res["error"])
        
        competitors = [
            CompetitorEntry(
                domain=c.get("domain", ""),
                rank=c.get("rank", 0),
                title=c.get("title"),
                url=c.get("link")
            )
            for c in res.get("competitors", [])
        ]
        
        return CompetitorGapResult(
            competitors=competitors,
            opportunities=res.get("opportunities", []),
            summary=res.get("summary", "")
        )
    except Exception as e:
        raise KeylyticsAPIError(f"Competitor gap tool failed: {e}") from e
