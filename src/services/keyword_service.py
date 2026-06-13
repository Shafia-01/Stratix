import streamlit as st
from src.logger_config import get_logger

logger = get_logger(__name__)

@st.cache_data(ttl=1800)
def cached_run_lightweight_agent(keyword, limit):
    from src.lightweight_agent import run_lightweight_agent
    from src.schemas import schemas_to_legacy_dicts
    results = run_lightweight_agent(keyword, limit)
    return schemas_to_legacy_dicts(results)

@st.cache_data(ttl=3600)
def cached_run_agent(keyword, limit):
    """
    Cached agent runner.
    """
    from src.agent import run_agent
    from src.schemas import schemas_to_legacy_dicts
    results = run_agent(keyword, limit)
    if results and len(results) < limit:
        logger.warning(f"Requested {limit} keywords but only got {len(results)}. This may be due to API limitations.")
    return schemas_to_legacy_dicts(results)

def prepare_keyword_records(keyword_results, seed_keyword):
    """Ensure keyword dictionaries include required defaults before saving."""
    if not keyword_results:
        return []
    normalized = []
    for item in keyword_results:
        if not isinstance(item, dict):
            continue
        record = item.copy()
        if seed_keyword and not record.get("seed"):
            record["seed"] = seed_keyword
        record["score"] = float(record.get("score") or 0)
        record["difficulty"] = record.get("difficulty") or "Unknown"
        record["intent"] = record.get("intent") or "Informational"
        normalized.append(record)
    return normalized

def save_keyword_results(data):
    """Save keyword results to DB without caching."""
    from src.db_client import save_to_db
    return save_to_db(data)

# Alias for compatibility
cached_save_to_db = save_keyword_results

@st.cache_data(ttl=300)
def cached_fetch_past_results(limit=50):
    """Cached version of fetch_past_results for better performance."""
    from src.db_client import fetch_past_results
    return fetch_past_results(limit)

@st.cache_data(ttl=1800)
def cached_verify_database_schema():
    """Cached version of database schema verification."""
    from src.db_client import verify_database_schema
    return verify_database_schema()
