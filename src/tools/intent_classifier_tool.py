from pydantic import BaseModel, Field
from src.intent_classifier import classify_intent_with_source
from src.schemas import IntentClassification
from src.exceptions import KeylyticsAPIError

class IntentClassifierInput(BaseModel):
    keyword: str = Field(..., description="The keyword to classify the search intent for")

def run(input: IntentClassifierInput) -> IntentClassification:
    """Execute intent classification tool."""
    try:
        intent, source = classify_intent_with_source(input.keyword)
        # Normalize source string to match the Literal["cache", "rule", "gemini"]
        # In case classify_intent_with_source returned something else.
        if source not in ["cache", "rule", "gemini"]:
            source = "rule"
        return IntentClassification(
            keyword=input.keyword,
            intent=intent,
            source=source
        )
    except Exception as e:
        raise KeylyticsAPIError(f"Intent classification tool failed: {e}") from e
