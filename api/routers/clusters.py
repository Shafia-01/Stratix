from fastapi import APIRouter, HTTPException
from src.tools.topic_cluster_tool import run as run_topic_cluster, TopicClusterInput
from src.schemas import TopicClusterResult
from src.exceptions import KeylyticsAPIError, KeylyticsDataError
from src.security_utils import redact_api_keys
from src.logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/topic", response_model=TopicClusterResult)
def topic_clustering(req: TopicClusterInput):
    logger.info("POST /api/v1/clusters/topic")
    try:
        return run_topic_cluster(req)
    except (KeylyticsAPIError, KeylyticsDataError) as e:
        redacted_msg = redact_api_keys(str(e))
        logger.error(f"API/Data error in topic_clustering: {redacted_msg}")
        raise HTTPException(status_code=502, detail=redacted_msg)
    except Exception as e:
        redacted_msg = redact_api_keys(str(e))
        logger.error(f"Unexpected error in topic_clustering: {redacted_msg}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
