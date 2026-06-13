import pandas as pd
import streamlit as st
from datetime import datetime
from src.services.keyword_service import cached_fetch_past_results
from src.logger_config import get_logger

logger = get_logger(__name__)

def update_global_metrics(keyword_results):
    """Update global metrics based on keyword analysis results"""
    if keyword_results:
        df = pd.DataFrame(keyword_results) if isinstance(keyword_results, list) else keyword_results        
        # Update total keywords
        current_total = st.session_state.get("total_keywords", 0)
        st.session_state.total_keywords = current_total + len(df)
        # Update average volume
        if 'volume' in df.columns:
            current_avg = st.session_state.get("avg_volume", 0)
            new_avg = df['volume'].mean()
            # Calculate weighted average
            total_count = st.session_state.total_keywords
            if total_count > 0:
                st.session_state.avg_volume = (current_avg * (total_count - len(df)) + new_avg * len(df)) / total_count        
        # Update opportunities (keywords with high scores)
        if 'score' in df.columns:
            high_score_keywords = len(df[df['score'] > 7.0])  # Assuming score > 7 is high opportunity
            current_opps = st.session_state.get("opportunities", 0)
            st.session_state.opportunities = current_opps + high_score_keywords        
        # Update trend score
        if 'score' in df.columns:
            current_trend = st.session_state.get("trend_score", 0)
            new_trend = df['score'].mean()
            # Calculate weighted average
            total_count = st.session_state.total_keywords
            if total_count > 0:
                st.session_state.trend_score = (current_trend * (total_count - len(df)) + new_trend * len(df)) / total_count

def increment_daily_requests(count=1):
    """Increment the daily request counter with automatic daily reset."""
    today = datetime.now().date().isoformat()
    if st.session_state.get("daily_request_date") != today:
        st.session_state.daily_requests = 0
        st.session_state.daily_request_date = today
    st.session_state.daily_requests = st.session_state.get("daily_requests", 0) + max(count, 0)

def add_recent_search(keyword):
    """Track up to the 10 most recent unique searches."""
    if not keyword:
        return
    keyword = keyword.strip()
    if not keyword:
        return
    history = st.session_state.get("search_history", [])
    if keyword in history:
        history.remove(keyword)
    history.append(keyword)
    st.session_state.search_history = history[-10:]

def initialize_metrics_from_history():
    """Seed global metrics from recent database history (runs once per session)."""
    if st.session_state.get("metrics_initialized"):
        return
    try:
        history_df = cached_fetch_past_results(limit=200)
        if history_df is not None and not history_df.empty:
            st.session_state.total_keywords = int(history_df.shape[0])
            if 'score' in history_df.columns:
                st.session_state.trend_score = float(history_df['score'].mean())
                st.session_state.opportunities = int((history_df['score'] > 7.0).sum())
            if 'volume' in history_df.columns:
                st.session_state.avg_volume = float(history_df['volume'].mean())
    except Exception as e:
        logger.exception("Metrics initialization skipped")
    finally:
        st.session_state.metrics_initialized = True
