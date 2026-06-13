from pydantic import BaseModel, Field
from src.serp_analyzer import analyze_serp_opportunities
from src.schemas import SerpAnalysisResult
from src.exceptions import KeylyticsAPIError

class SerpAnalysisInput(BaseModel):
    keyword: str = Field(..., description="The keyword to analyze the SERP for")
    num_results: int = Field(10, description="Number of results to analyze")

def run(input: SerpAnalysisInput) -> SerpAnalysisResult:
    """Execute SERP analysis tool."""
    try:
        res = analyze_serp_opportunities(input.keyword, input.num_results)
        if isinstance(res, dict) and "error" in res:
            raise KeylyticsAPIError(res["error"])
        return SerpAnalysisResult(
            keyword=res.get("keyword", ""),
            serp_data=res.get("serp_data", {}),
            snippet_analysis=res.get("snippet_analysis", {}),
            paa_questions=res.get("paa_questions", {}),
            ranking_analysis=res.get("ranking_analysis", {}),
            content_gaps=res.get("content_gaps", {}),
            optimization_suggestions=res.get("optimization_suggestions", []),
            summary=res.get("summary", "")
        )
    except Exception as e:
        raise KeylyticsAPIError(f"SERP analysis tool failed: {e}") from e
