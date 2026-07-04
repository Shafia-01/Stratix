import streamlit as st
from datetime import datetime

def initialize_session_state():
    """Initialize session state variables."""
    return {
        "current_page": "landing",
        "keyword_results": [],
        "competitor_results": None,
        "cluster_results": None,
        "trend_results": None,
        "serp_results": None,
        "search_history": [],
        "daily_requests": 0,
        "daily_request_date": datetime.now().date().isoformat(),
        "total_keywords": 0,
        "opportunities": 0,
        "avg_volume": 0,
        "trend_score": 0,
        "metrics_initialized": False
    }

def setup_session_state():
    """Ensure session state default variables exist in st.session_state."""
    session_defaults = initialize_session_state()
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
