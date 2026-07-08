import streamlit as st
from src.logger_config import get_logger
from src.services.status_service import get_system_status
from src.services.keyword_service import cached_fetch_past_results, cached_verify_database_schema

logger = get_logger(__name__)

def render_sidebar():
    st.sidebar.markdown("""
    <div class="sidebar-header" style="text-align: center; margin-bottom: 20px;">
        <h2 style="font-family: 'Cambria', serif; font-size: 1.3rem; font-weight: bold; color: #051B4A; margin: 0 0 10px 0;">Autonomous Multi-Agent Market Intelligence Platform</h2>
        <hr style="border: none; height: 1.5px; background: #051B4A; margin: 10px 0; border-radius: 1.5px;" />
        <p style="font-size: 0.75rem; color: #232527; font-weight: bold; margin-top: 5px;">Powered by LangGraph · Gemini · 6 Specialized Tools</p>
    </div>
    """, unsafe_allow_html=True)

    # System Status Card
    api_status, api_test = get_system_status()
    system_status_html = f"""
    <div style="display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;">
            <span style="color: #232527; font-weight: 500;">Gemini API</span>
            <span style="font-weight: 600; color: {'#10B981' if api_test['gemini'] else '#EF4444'};">{'Online' if api_test['gemini'] else 'Offline'}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;">
            <span style="color: #232527; font-weight: 500;">SerpApi</span>
            <span style="font-weight: 600; color: {'#10B981' if api_test['serpapi'] else '#EF4444'};">{'Online' if api_test['serpapi'] else 'Offline'}</span>
        </div>
    </div>
    """
    from src.ui.components import render_card
    render_card(
        title="System Status",
        content_html=system_status_html,
        icon='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#051B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>',
        sidebar=True
    )

    # Model Status Card
    from src.services.status_service import GEMINI_MODELS
    model_status_html = f"""
    <div style="display: flex; flex-direction: column; gap: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;">
            <span style="color: #232527; font-weight: 500;">Model Type</span>
            <span style="font-weight: 600; color: #051B4A;">Primary + {len(GEMINI_MODELS) - 1} Fallbacks</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;">
            <span style="color: #232527; font-weight: 500;">Active Models</span>
            <span style="font-weight: 600; color: #051B4A;">{len(GEMINI_MODELS)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.9rem;">
            <span style="color: #232527; font-weight: 500;">Requests Today</span>
            <span style="font-weight: 600; color: #051B4A;">{st.session_state.get("daily_requests", 0)}</span>
        </div>
    </div>
    """
    render_card(
        title="Model Status",
        content_html=model_status_html,
        icon='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#051B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path><line x1="8" y1="16" x2="8" y2="16"></line><line x1="16" y1="16" x2="16" y2="16"></line></svg>',
        sidebar=True
    )

    if st.sidebar.button("Check Database Status", use_container_width=True):
        with st.spinner("Checking database..."):
            try:
                schema_ok = cached_verify_database_schema()
                df_test = cached_fetch_past_results(limit=1)
                if schema_ok and not df_test.empty:
                     st.session_state.db_status = f"Connected ({len(df_test)} records)"
                elif schema_ok:
                     st.session_state.db_status = "Connected (0 records)"
                else:
                     st.session_state.db_status = "Schema issues detected"
            except Exception as e:
                error_msg = str(e)
                if "Access denied" in error_msg:
                     st.session_state.db_status = "Access denied - Check credentials"
                elif "Can't connect" in error_msg or "Connection refused" in error_msg:
                     st.session_state.db_status = "Can't connect - Check if MySQL is running"
                elif "Unknown database" in error_msg:
                     st.session_state.db_status = "Database doesn't exist"
                else:
                     st.session_state.db_status = f"Connection failed: {error_msg[:50]}..."
        st.rerun()

    if 'db_status' in st.session_state:
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            if "Connection failed" in st.session_state.db_status or "denied" in st.session_state.db_status or "Can't connect" in st.session_state.db_status:
                st.sidebar.error(st.session_state.db_status)
            elif "issues" in st.session_state.db_status:
                st.sidebar.warning(st.session_state.db_status)
            else:
                st.sidebar.success(st.session_state.db_status)
        with col2:
            if st.sidebar.button("Clear", help="Clear status", key="clear_db_status"):
                del st.session_state.db_status
                st.rerun()

    if st.sidebar.button("Home Dashboard", type="primary", use_container_width=True):
        st.session_state.current_page = "home"
        st.rerun()

    st.sidebar.markdown('<div style="font-family: \'Cambria\', Georgia, serif; font-size: 0.95rem; font-weight: 600; color: #051B4A; margin: 20px 0 10px 0;">Single-Shot Tools</div>', unsafe_allow_html=True)

    if st.sidebar.button("Keyword Discovery", use_container_width=True):
        st.session_state.current_page = "keyword_discovery"
        st.rerun()
    if st.sidebar.button("Competitor Gap", use_container_width=True):
        st.session_state.current_page = "competitor_gap"
        st.rerun()
    if st.sidebar.button("SERP Analysis", use_container_width=True):
        st.session_state.current_page = "serp_analysis"
        st.rerun()
    if st.sidebar.button("Topic Clustering", use_container_width=True):
        st.session_state.current_page = "topic_clustering"
        st.rerun()
    if st.sidebar.button("Trend Forecasting", use_container_width=True):
        st.session_state.current_page = "trend_forecasting"
        st.rerun()
    if st.sidebar.button("Full Strategy Utility", use_container_width=True):
        st.session_state.current_page = "full_strategy"
        st.rerun()

    st.sidebar.markdown('<div style="font-family: \'Cambria\', Georgia, serif; font-size: 0.95rem; font-weight: 600; color: #051B4A; margin: 20px 0 10px 0;">Recent Searches</div>', unsafe_allow_html=True)
    if st.session_state.search_history:
        for i, search in enumerate(st.session_state.search_history[-3:]):
            if st.sidebar.button(f"{search[:25]}...", key=f"history_{i}", use_container_width=True):
                st.session_state.selected_keyword = search
                st.session_state.current_page = "keyword_discovery"
                st.rerun()
    else:
        st.sidebar.info("No recent searches")
