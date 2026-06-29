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
    st.sidebar.markdown("### 🔧 System Status")
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
    st.sidebar.markdown("### 🤖 Model Status")
    from src.services.status_service import GEMINI_MODELS
    st.sidebar.markdown("""
    <div class="system-status">
        <div class="status-item">
            <span class="status-label">Model Type</span>
            <span class="status-value">Gemini 2.5 Flash</span>
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
    """.format(len(GEMINI_MODELS), st.session_state.get("daily_requests", 0)), unsafe_allow_html=True)
    # Database Status (simplified)
    st.sidebar.markdown("### 💾 Database")
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
    # Database History
    st.sidebar.markdown("### 📂 Database History")
    if st.sidebar.button("📂 Intelligence Archive", use_container_width=True):
        st.session_state.current_page = "search_history"
        st.rerun()

    # Agent Mode
    st.sidebar.markdown("### 🤖 Autonomous Agent")
    if st.sidebar.button("🤖 Autonomous Pipeline", use_container_width=True):
        st.session_state.current_page = "agent_mode"
        st.rerun()

    # Execution Timeline
    st.sidebar.markdown("### 🗂️ Execution Timeline")
    if st.sidebar.button("🗂️ Execution Timeline", use_container_width=True):
        st.session_state.current_page = "agent_timeline"
        st.rerun()

    # Monitoring Dashboard
    st.sidebar.markdown("### 🛡️ Monitoring & Evaluation")
    if st.sidebar.button("🛡️ Intelligence Monitor", use_container_width=True):
        st.session_state.current_page = "monitoring_dashboard"
        st.rerun()

    # Recent Searches (optimized)
    st.sidebar.markdown("### 🔍 Recent Searches")
    # Display recent searches from session state only
    if st.session_state.search_history:
        for i, search in enumerate(st.session_state.search_history[-3:]):
            if st.sidebar.button(f"🔍 {search[:25]}...", key=f"history_{i}", use_container_width=True):
                st.session_state.selected_keyword = search
                st.session_state.current_page = "keyword_discovery"
                st.rerun()
    else:
        st.sidebar.info("No recent searches")
