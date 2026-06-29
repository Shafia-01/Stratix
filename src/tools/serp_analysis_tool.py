from pydantic import BaseModel, Field
from src.serp_analyzer import analyze_serp_opportunities
from src.schemas import (
    SerpAnalysisResult, SerpRawData, OrganicResult, SnippetAnalysis,
    SnippetOpportunity, PAAData, PAAQuestion
)
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

        raw_serp = res.get("serp_data", {})
        serp_data_typed = SerpRawData(
            organic_results=[OrganicResult(**r) for r in raw_serp.get("organic_results", []) if isinstance(r, dict)],
            people_also_ask=raw_serp.get("people_also_ask", []),
            related_searches=raw_serp.get("related_searches", []),
            featured_snippet=raw_serp.get("featured_snippet", {}),
            search_information=raw_serp.get("search_information", {}),
        )

        raw_sa = res.get("snippet_analysis", {})
        snippet_analysis_typed = SnippetAnalysis(
            has_featured_snippet=raw_sa.get("has_featured_snippet", False),
            snippet_opportunities=[
                SnippetOpportunity(**opp)
                for opp in raw_sa.get("snippet_opportunities", [])
                if isinstance(opp, dict)
            ]
        )

        raw_paa = res.get("paa_questions", {})
        paa_typed = PAAData(
            questions=[
                PAAQuestion(
                    question=q.get("question", ""),
                    snippet=q.get("snippet", ""),
                    content_idea=q.get("content_idea", ""),
                    opportunity_type=q.get("opportunity_type"),
                )
                for q in raw_paa.get("questions", [])
                if isinstance(q, dict)
            ],
            opportunities=raw_paa.get("opportunities", []),
        )

        suggestions_typed = [
            SnippetOpportunity(
                type=s.get("type", ""),
                opportunity=s.get("opportunity", ""),
                recommendation=s.get("recommendation", ""),
                priority=s.get("priority", "low") if s.get("priority") in ("high", "medium", "low") else "low",
            )
            for s in res.get("optimization_suggestions", [])
            if isinstance(s, dict)
        ]

        return SerpAnalysisResult(
            keyword=res.get("keyword", ""),
            serp_data=serp_data_typed,
            snippet_analysis=snippet_analysis_typed,
            paa_questions=paa_typed,
            ranking_analysis=res.get("ranking_analysis", {}),
            content_gaps=res.get("content_gaps", {}),
            optimization_suggestions=suggestions_typed,
            summary=res.get("summary", "")
        )
    except Exception as e:
        raise KeylyticsAPIError(f"SERP analysis tool failed: {e}") from e
