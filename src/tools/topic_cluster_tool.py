"""
Topic clustering tool for Keylytics.

Input: List[str] — plain keyword strings (LLM tool-callers produce simple JSON
arrays, not nested Pydantic objects). Any KeywordFinding objects passed by
internal Python callers are normalised to strings before dispatch.

Output: TopicClusterResult with fully typed List[TopicClusterEntry] clusters.
"""

from typing import List
from pydantic import BaseModel, Field
from src.topic_clusterer import cluster_keywords_semantically
from src.schemas import TopicClusterResult, TopicClusterEntry, ClusterMetrics
from src.exceptions import KeylyticsAPIError


class TopicClusterInput(BaseModel):
    # Accepts List[str] only — LLM agents send plain JSON arrays.
    # Internal callers with KeywordFinding objects should call
    # [kf.keyword for kf in findings] before invoking this tool.
    keywords: List[str] = Field(
        ...,
        description="List of keyword strings to cluster semantically. "
                    "Pass plain strings, not nested objects.",
    )


def run(input: TopicClusterInput) -> TopicClusterResult:
    """Execute semantic topic clustering tool."""
    try:
        # Normalise to the dict format expected by cluster_keywords_semantically
        normalized = [{"keyword": kw} for kw in input.keywords]

        res = cluster_keywords_semantically(normalized)
        if isinstance(res, dict) and "error" in res:
            raise KeylyticsAPIError(res["error"])

        # Build typed TopicClusterEntry models from raw cluster dicts
        typed_clusters: List[TopicClusterEntry] = []
        for raw in res.get("clusters", []):
            metrics_raw = raw.get("metrics") or {}
            typed_clusters.append(
                TopicClusterEntry(
                    cluster_name=raw.get("cluster_name", "Unknown"),
                    description=raw.get("description", ""),
                    keywords=raw.get("keywords", []),
                    primary_intent=raw.get("primary_intent", "informational"),
                    industry_focus=raw.get("industry_focus", "general"),
                    keyword_count=raw.get("keyword_count", len(raw.get("keywords", []))),
                    opportunity_score=float(raw.get("opportunity_score", 0.0)),
                    metrics=ClusterMetrics(
                        avg_volume=float(metrics_raw.get("avg_volume", 0.0)),
                        avg_competition=float(metrics_raw.get("avg_competition", 0.0)),
                        avg_cpc=float(metrics_raw.get("avg_cpc", 0.0)),
                        avg_score=float(metrics_raw.get("avg_score", 0.0)),
                        total_volume=float(metrics_raw.get("total_volume", 0.0)),
                    ),
                )
            )

        # Format insights list
        insights_list: List[str] = []
        for insight in res.get("insights", []):
            if isinstance(insight, dict):
                insights_list.append(f"{insight.get('title', '')}: {insight.get('description', '')}")
            else:
                insights_list.append(str(insight))

        return TopicClusterResult(
            clusters=typed_clusters,
            insights=insights_list,
            summary=res.get("summary", ""),
        )
    except KeylyticsAPIError:
        raise
    except Exception as exc:
        raise KeylyticsAPIError(f"Topic cluster tool failed: {exc}") from exc
