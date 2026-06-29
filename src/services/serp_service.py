import streamlit as st
from src.logger_config import get_logger

logger = get_logger(__name__)

@st.cache_data(ttl=1800)
def cached_analyze_serp_opportunities(keyword):
    """
    Cached version of analyze_serp_opportunities.
    """
    from src.serp_analyzer import analyze_serp_opportunities
    return analyze_serp_opportunities(keyword)
