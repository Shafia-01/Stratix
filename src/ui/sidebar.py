import streamlit as st
from src.logger_config import get_logger
from src.services.status_service import get_system_status
from src.services.keyword_service import cached_fetch_past_results, cached_verify_database_schema

logger = get_logger(__name__)

def render_sidebar():
    st.sidebar.markdown("""
    <div class="sidebar-header">
        <h2>Autonomous Multi-Agent Market Intelligence Platform</h2>
        <hr style="border: none; height: 2px; background: #051B4A; margin: 10px 0; border-radius: 1.5px;" />
        <p style="font-size: 0.75rem; color: #232527; font-weight: bold; margin-top: 5px;">Powered by LangGraph · Gemini · 6 Specialized Tools</p>
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("<h3 style='text-align: center;'>🔧 System Status</h3>", unsafe_allow_html=True)
    api_status, api_test = get_system_status()
    st.sidebar.markdown("""
    <div class="system-status">
        <div class="status-item">
            <span class="status-label">Gemini API</span>
            <span class="status-value {}">{}</span>
        </div>
        <div class="status-item">
            <span class="status-label">SerpApi</span>
            <span class="status-value {}">{}</span>
        </div>
    </div>
    """.format(
        "status-online" if api_test["gemini"] else "status-offline",
        "✅ Online" if api_test["gemini"] else "❌ Offline",
        "status-online" if api_test["serpapi"] else "status-offline",
        "✅ Online" if api_test["serpapi"] else "❌ Offline"
    ), unsafe_allow_html=True)
    # Model Status
    st.sidebar.markdown("<h3 style='text-align: center;'>🤖 Model Status</h3>", unsafe_allow_html=True)
    from src.services.status_service import GEMINI_MODELS
    st.sidebar.markdown("""
    <div class="system-status">
        <div class="status-item">
            <span class="status-label">Model Type</span>
            <span class="status-value">Primary + {} Fallbacks</span>
        </div>
        <div class="status-item">
            <span class="status-label">Active Models</span>
            <span class="status-value">{}</span>
        </div>
        <div class="status-item">
            <span class="status-label">Requests Today</span>
            <span class="status-value">{}</span>
        </div>
    </div>
    """.format(len(GEMINI_MODELS) - 1, len(GEMINI_MODELS), st.session_state.get("daily_requests", 0)), unsafe_allow_html=True)
    # Use a placeholder that doesn't make heavy DB calls on every render
    if st.sidebar.button("🔍 Check Database Status", use_container_width=True):
        with st.spinner("Checking database..."):
            try:
                schema_ok = cached_verify_database_schema()
                df_test = cached_fetch_past_results(limit=1)
                if schema_ok and not df_test.empty:
                     st.session_state.db_status = f"✅ Connected ({len(df_test)} records)"
                elif schema_ok:
                     st.session_state.db_status = "✅ Connected (0 records)"
                else:
                     st.session_state.db_status = "⚠️ Schema issues detected"
            except Exception as e:
                error_msg = str(e)
                if "Access denied" in error_msg:
                     st.session_state.db_status = "❌ Access denied - Check credentials"
                elif "Can't connect" in error_msg or "Connection refused" in error_msg:
                     st.session_state.db_status = "❌ Can't connect - Check if MySQL is running"
                elif "Unknown database" in error_msg:
                     st.session_state.db_status = "❌ Database doesn't exist"
                else:
                     st.session_state.db_status = f"❌ Connection failed: {error_msg[:50]}..."
        st.rerun()

    # Display the last database check result if available
    if 'db_status' in st.session_state:
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            if st.session_state.db_status.startswith("✅"):
                st.sidebar.success(st.session_state.db_status)
            elif st.session_state.db_status.startswith("⚠️"):
                st.sidebar.warning(st.session_state.db_status)
            elif st.session_state.db_status.startswith("❌"):
                st.sidebar.error(st.session_state.db_status)
            else:
                st.sidebar.info(st.session_state.db_status)
        with col2:
            if st.sidebar.button("🗑️", help="Clear status", key="clear_db_status"):
                del st.session_state.db_status
                st.rerun()
    st.sidebar.markdown("<h3 style='text-align: center;'>🗺️ Navigation</h3>", unsafe_allow_html=True)

    if st.sidebar.button("🤖 Autonomous Research", use_container_width=True):
        st.session_state.current_page = "agent_mode"
        st.rerun()

    if st.sidebar.button("📈 Executive Reports", use_container_width=True):
        st.session_state.current_page = "executive_reports"
        st.rerun()

    if st.sidebar.button("📊 Unified Analytics", use_container_width=True):
        st.session_state.current_page = "analytics"
        st.rerun()

    if st.sidebar.button("🛡️ Intelligence Monitor", use_container_width=True):
        st.session_state.current_page = "monitoring_dashboard"
        st.rerun()

    # Collapsible tools section
    with st.sidebar.expander("🔧 Single-Shot Tools", expanded=False):
        if st.button("🔑 Keyword Discovery", use_container_width=True):
            st.session_state.current_page = "keyword_discovery"
            st.rerun()
        if st.button("🧩 Competitor Gap", use_container_width=True):
            st.session_state.current_page = "competitor_gap"
            st.rerun()
        if st.button("📰 SERP Analysis", use_container_width=True):
            st.session_state.current_page = "serp_analysis"
            st.rerun()
        if st.button("🧠 Topic Clustering", use_container_width=True):
            st.session_state.current_page = "topic_clustering"
            st.rerun()
        if st.button("📈 Trend Forecasting", use_container_width=True):
            st.session_state.current_page = "trend_forecasting"
            st.rerun()
        if st.button("⚡ Full Strategy Utility", use_container_width=True):
            st.session_state.current_page = "full_strategy"
            st.rerun()

    # Recent Searches (optimized)
    st.sidebar.markdown("<h3 style='text-align: center;'>🔍 Recent Searches</h3>", unsafe_allow_html=True)
    # Display recent searches from session state only
    if st.session_state.search_history:
        for i, search in enumerate(st.session_state.search_history[-3:]):
            if st.sidebar.button(f"🔍 {search[:25]}...", key=f"history_{i}", use_container_width=True):
                st.session_state.selected_keyword = search
                st.session_state.current_page = "keyword_discovery"
                st.rerun()
    else:
        st.sidebar.info("No recent searches")
