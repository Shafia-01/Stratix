import streamlit as st
import os
from dotenv import load_dotenv

# Initialize session state first thing
from src.ui.state import setup_session_state
setup_session_state()

from src.logger_config import get_logger
logger = get_logger("app")

# Set up page configurations
st.set_page_config(page_title="Keylytics — Market Intelligence Platform", page_icon="🔑", layout="wide", initial_sidebar_state="expanded")

# Lazy imports for heavier libraries
def lazy_imports():
    import pandas as pd
    import json
    import plotly.express as px
    import plotly.graph_objects as go
    return pd, json, px, go
pd, json, px, go = lazy_imports()

load_dotenv()

# Services
from src.services.status_service import check_api_status, test_api_quick
from src.services.metrics_service import initialize_metrics_from_history

# UI Theme, Components, and Pages
from src.ui.theme import load_custom_css
load_custom_css()

from src.ui.sidebar import render_sidebar
from src.ui.home import render_home_overview, render_floating_panel
from src.ui.keyword_discovery import render_keyword_discovery
from src.ui.competitor_gap import render_competitor_gap
from src.ui.topic_clustering import render_topic_clustering
from src.ui.trend_forecasting import render_trend_forecasting
from src.ui.serp_analysis import render_serp_analysis
from src.ui.full_strategy import render_full_strategy
from src.ui.search_history import render_search_history
from src.ui.agent_mode import render_agent_mode


def handle_api_errors():
    """Display API status."""
    api_status = check_api_status()
    if not api_status["GEMINI_API_KEY"]:
        st.error("⚠️ **GEMINI_API_KEY not found!** Please add it to your .env file.")
    if not api_status["SERPAPI_KEY"]:
        st.warning("⚠️ **SERPAPI_KEY not found!** Some features may not work properly.")

def main():
    initialize_metrics_from_history()
    api_status = check_api_status()
    api_test = test_api_quick()
    if not api_status["GEMINI_API_KEY"] or not api_status["SERPAPI_KEY"]:
        with st.expander("⚠️ API Configuration Issues", expanded=True):
            handle_api_errors()
    elif not api_test["gemini"] or not api_test["serpapi"]:
        with st.expander("⚠️ API Connection Issues", expanded=True):
            st.error("API keys found but connections are failing!")
            
            if not api_test["gemini"]:
                st.error("🔴 **Gemini API Failed**")
                st.info("💡 **Possible fixes:**")
                st.info("• Check if your API key is valid")
                st.info("• Verify internet connection")
                st.info("• Try refreshing the page")
                st.info("• Check Google AI Studio for service status")
            
            if not api_test["serpapi"]:
                st.error("🔴 **SerpApi Failed**")
                st.info("💡 **Possible fixes:**")
                st.info("• Check if your API key is valid")
                st.info("• Verify you have remaining searches in your account")
                st.info("• Check SerpApi service status")
                st.info("• Try refreshing the page")
            
            if api_test["gemini"] and not api_test["serpapi"]:
                st.success("✅ **Working Features:** Keyword Analysis, Topic Clustering, Trend Forecasting, Chat Assistant")
                st.warning("⚠️ **Limited Features:** SERP Analysis and Competitor Gap Analysis may not work")
            
            if st.button("🔄 Retest APIs", type="secondary"):
                st.rerun()

    render_sidebar()
    col1, col2, col3, col4, col5 = st.columns(5)
    with col5:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_page = "home"
            st.rerun()
        toggle_text = "Hide Features" if st.session_state.get("panel_open", False) else "Show Features"
        if st.button(toggle_text, use_container_width=True):
            st.session_state.panel_open = not st.session_state.get("panel_open", False)
            st.rerun()
    render_floating_panel()
    current_page = st.session_state.current_page
    
    if current_page == "home":
        render_home_overview()
    elif current_page == "keyword_discovery":
        render_keyword_discovery()
    elif current_page == "competitor_gap":
        render_competitor_gap()
    elif current_page == "topic_clustering":
        render_topic_clustering()
    elif current_page == "trend_forecasting":
        render_trend_forecasting()
    elif current_page == "serp_analysis":
        render_serp_analysis()
    elif current_page == "full_strategy":
        render_full_strategy()
    elif current_page == "search_history":
        render_search_history()
    elif current_page == "agent_mode":
        render_agent_mode()
    elif current_page == "agent_timeline":
        from src.ui.agent_timeline import render_agent_timeline
        render_agent_timeline()
    elif current_page == "monitoring_dashboard":
        from src.ui.monitoring_dashboard import render_monitoring_dashboard
        render_monitoring_dashboard()
    else:
        render_home_overview()


if __name__ == "__main__":
    main()

