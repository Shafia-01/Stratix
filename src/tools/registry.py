"""
Tool registry for Keylytics — single source of truth for all available tools.

invoke_tool() provides a safe, exception-eating dispatch entry point for
agent loops (LangGraph Phase 3). Errors are returned as {"error": ..., "tool": name}
so the agent receives structured error results, not raised exceptions.
"""

from typing import Callable, Dict, List, Type, Any
from pydantic import BaseModel, ValidationError
from src.tools.keyword_research_tool import KeywordResearchInput, run as run_keyword_research
from src.tools.serp_analysis_tool import SerpAnalysisInput, run as run_serp_analysis
from src.tools.competitor_gap_tool import CompetitorGapInput, run as run_competitor_gap
from src.tools.trend_forecast_tool import TrendForecastInput, run as run_trend_forecast
from src.tools.topic_cluster_tool import TopicClusterInput, run as run_topic_cluster
from src.tools.intent_classifier_tool import IntentClassifierInput, run as run_intent_classifier
from src.exceptions import KeylyticsAPIError
from src.logger_config import get_logger

logger = get_logger(__name__)


class ToolSpec(BaseModel):
    name: str
    description: str
    input_model: Type[BaseModel]
    output_model: Any
    fn: Callable

    model_config = {
        "arbitrary_types_allowed": True
    }


TOOL_REGISTRY: Dict[str, ToolSpec] = {
    "keyword_research": ToolSpec(
        name="keyword_research",
        description="Discover and research related keywords for a seed term with search volume, CPC, and competition metrics.",
        input_model=KeywordResearchInput,
        output_model=Any,  # List[KeywordSuggestion]
        fn=run_keyword_research
    ),
    "serp_analysis": ToolSpec(
        name="serp_analysis",
        description="Analyze search engine results pages to find snippet optimizations, content gaps, and People Also Ask questions.",
        input_model=SerpAnalysisInput,
        output_model=Any,  # SerpAnalysisResult
        fn=run_serp_analysis
    ),
    "competitor_gap": ToolSpec(
        name="competitor_gap",
        description="Perform competitor keyword gap analysis to identify traffic opportunities that competitors rank for.",
        input_model=CompetitorGapInput,
        output_model=Any,  # CompetitorGapResult
        fn=run_competitor_gap
    ),
    "trend_forecast": ToolSpec(
        name="trend_forecast",
        description="Predict keyword search trends and seasonality patterns for a list of keywords over the next 6 months.",
        input_model=TrendForecastInput,
        output_model=Any,  # TrendForecastResult
        fn=run_trend_forecast
    ),
    "topic_cluster": ToolSpec(
        name="topic_cluster",
        description="Cluster a list of keywords semantically into topic groupings for content strategy mapping.",
        input_model=TopicClusterInput,
        output_model=Any,  # TopicClusterResult
        fn=run_topic_cluster
    ),
    "intent_classifier": ToolSpec(
        name="intent_classifier",
        description="Classify the search intent of a keyword as informational, commercial, transactional, or navigational.",
        input_model=IntentClassifierInput,
        output_model=Any,  # IntentClassification
        fn=run_intent_classifier
    )
}


def get_tool_schemas() -> List[dict]:
    """Generate tool schemas formatted for Anthropic's tool-use API."""
    schemas = []
    for spec in TOOL_REGISTRY.values():
        schemas.append({
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_model.model_json_schema()
        })
    return schemas


def invoke_tool(name: str, raw_args: dict) -> dict:
    """
    Look up a tool by name, validate raw_args against its input_model,
    execute the tool function, and return a JSON-serialisable dict result.

    This is the canonical dispatch entry point for agent loops (LangGraph Phase 3).
    Errors — including KeylyticsAPIError and pydantic.ValidationError — are
    caught and returned as {"error": <message>, "tool": <name>} so that
    agent loops receive structured results, not raised exceptions.

    Args:
        name:     The tool name as registered in TOOL_REGISTRY.
        raw_args: Raw dict of arguments; validated against the tool's input_model.

    Returns:
        A JSON-serialisable dict of the tool result, or
        {"error": str, "tool": name} if anything goes wrong.
    """
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        return {"error": f"Unknown tool: '{name}'", "tool": name}

    try:
        validated_input = spec.input_model.model_validate(raw_args)
    except ValidationError as exc:
        logger.warning(f"invoke_tool validation error for '{name}': {exc}")
        return {"error": str(exc), "tool": name}

    try:
        result = spec.fn(validated_input)
    except (KeylyticsAPIError, Exception) as exc:
        logger.warning(f"invoke_tool execution error for '{name}': {exc}")
        return {"error": str(exc), "tool": name}

    # Serialise Pydantic models; plain dicts pass through unchanged
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, list):
        return {
            "items": [
                item.model_dump(mode="json") if isinstance(item, BaseModel) else item
                for item in result
            ]
        }
    if isinstance(result, dict):
        return result
    # Fallback: coerce to string representation
    return {"result": str(result)}
