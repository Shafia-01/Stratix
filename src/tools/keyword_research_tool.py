from typing import List
from pydantic import BaseModel, Field
from src.keyword_api_client import get_enhanced_keywords
from src.schemas import KeywordSuggestion
from src.exceptions import KeylyticsAPIError
from src.data_quality import DataSource

class KeywordResearchInput(BaseModel):
    seed_keyword: str = Field(..., description="Seed keyword to generate suggestions for")
    max_keywords: int = Field(50, description="Maximum number of keywords to return")

def run(input: KeywordResearchInput) -> List[KeywordSuggestion]:
    """Execute keyword research tool."""
    try:
        results = get_enhanced_keywords(input.seed_keyword, input.max_keywords)
        suggestions = []
        for r in results:
            suggestions.append(
                KeywordSuggestion(
                    keyword=r.get("keyword", ""),
                    volume=float(r.get("volume") or 0.0),
                    cpc=r.get("cpc"),
                    competition=r.get("competition"),
                    data_source=DataSource(r.get("data_source", DataSource.UNAVAILABLE.value))
                )
            )
        return suggestions
    except Exception as e:
        raise KeylyticsAPIError(f"Keyword research tool failed: {e}") from e
