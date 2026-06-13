from typing import List, Union, Any
from pydantic import BaseModel, Field
from src.topic_clusterer import cluster_keywords_semantically
from src.schemas import TopicClusterResult, KeywordFinding
from src.exceptions import KeylyticsAPIError

class TopicClusterInput(BaseModel):
    keywords: Union[List[KeywordFinding], List[str]] = Field(..., description="List of keyword findings or strings to cluster semantically")

def run(input: TopicClusterInput) -> TopicClusterResult:
    """Execute semantic topic clustering tool."""
    try:
        normalized = []
        for item in input.keywords:
            if isinstance(item, BaseModel):
                normalized.append(item.model_dump())
            else:
                normalized.append(item)
                
        res = cluster_keywords_semantically(normalized)
        if isinstance(res, dict) and "error" in res:
            raise KeylyticsAPIError(res["error"])
        
        # Format insights list if needed
        insights_list = []
        for insight in res.get("insights", []):
            if isinstance(insight, dict):
                insights_list.append(f"{insight.get('title')}: {insight.get('description')}")
            else:
                insights_list.append(str(insight))
                
        return TopicClusterResult(
            clusters=res.get("clusters", []),
            insights=insights_list,
            summary=res.get("summary", "")
        )
    except Exception as e:
        raise KeylyticsAPIError(f"Topic cluster tool failed: {e}") from e
