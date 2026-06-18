import streamlit as st
import base64

def load_base64_image(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def render_home_overview():
    try:
        logo_base64 = load_base64_image("assets/keylytics_icon.png")
    except Exception:
        logo_base64 = ""

    # Welcome section
    st.markdown(f"""
    <div style="width:100%; display:flex; justify-content:center;">
        <div class="home-container">
            <div class="welcome-section">
                <div class="app-logo" style="margin-bottom: -35px; margin-top: -150px;" >
                    <img src="data:image/png;base64,{logo_base64}" width="150" style="vertical-align:middle; margin:0; padding:0;" />
                </div>
                <h1 class="app-title">Stratix AI</h1>
                <p class="app-subtitle">Where Autonomous Agents Turn Market Signals into Strategy</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pipeline Status Section
    st.markdown("#### 🤖 Pipeline Status")
    status_data = {"active_runs": 0, "total_reports": 0, "active_jobs": 0}
    try:
        from src.db_client import connect_db
        from src.models import ResearchRunLog
        from sqlalchemy.orm import Session
        import requests
        import os

        API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

        # Check if API is reachable
        api_reachable = False
        try:
            health_resp = requests.get(f"{API_BASE_URL}/health", timeout=3)
            if health_resp.status_code == 200:
                api_reachable = True
        except Exception:
            pass

        engine = connect_db()
        with Session(engine) as session:
            if api_reachable:
                # Active runs: in progress/awaiting approval
                status_data["active_runs"] = session.query(ResearchRunLog).filter(
                    ResearchRunLog.status.in_(["pending", "in_progress", "awaiting_approval"])
                ).count()
            
            # Total Intelligence Reports from DB history count
            status_data["total_reports"] = session.query(ResearchRunLog).filter(
                ResearchRunLog.status == "completed"
            ).count()

        if api_reachable:
            try:
                headers = {}
                api_key = os.getenv("STRATIX_AI_API_KEY") or os.getenv("KEYLYTICS_API_KEY")
                if api_key:
                    headers["X-API-Key"] = api_key
                jobs_resp = requests.get(f"{API_BASE_URL}/monitor/jobs", headers=headers, timeout=3)
                if jobs_resp.status_code == 200:
                    status_data["active_jobs"] = len([j for j in jobs_resp.json() if j.get("status") == "active"])
            except Exception:
                pass
    except Exception:
        pass

    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Active Research Runs", status_data["active_runs"])
    with col_stat2:
        st.metric("Total Intelligence Reports", status_data["total_reports"])
    with col_stat3:
        st.metric("Active Monitoring Jobs", status_data["active_jobs"])

    # Quick buttons using Streamlit buttons
    st.markdown("### 🚀 Quick Actions")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("🔍 Research Pipeline", use_container_width=True):
            st.session_state.current_page = "keyword_discovery"
            st.rerun()
    with col2:
        if st.button("🎯 Competitor Intelligence", use_container_width=True):
            st.session_state.current_page = "competitor_gap"
            st.rerun()
    with col3:
        if st.button("📈 Market Trends", use_container_width=True):
            st.session_state.current_page = "trend_forecasting"
            st.rerun()
    with col4:
        if st.button("⚡ Full Intelligence Run", use_container_width=True):
            st.session_state.current_page = "full_strategy"
            st.rerun()
    with col5:
        if st.button("🤖 Autonomous Agent", use_container_width=True):
            st.session_state.current_page = "agent_mode"
            st.rerun()

    # Summary cards
    st.markdown("### 📊 Global Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="summary-card">
            <div class="summary-card-icon">🔍</div>
            <div class="summary-card-title">Keywords Analyzed</div>
            <div class="summary-card-value">{}</div>
            <div class="summary-card-desc">Total keywords processed</div>
        </div>
        """.format(st.session_state.get("total_keywords", 0)), unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="summary-card">
            <div class="summary-card-icon">📊</div>
            <div class="summary-card-title">Avg Volume</div>
            <div class="summary-card-value">{}</div>
            <div class="summary-card-desc">Average search volume</div>
        </div>
        """.format(f"{st.session_state.get('avg_volume', 0):.0f}"), unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="summary-card">
            <div class="summary-card-icon">🎯</div>
            <div class="summary-card-title">Opportunities</div>
            <div class="summary-card-value">{}</div>
            <div class="summary-card-desc">High-potential keywords</div>
        </div>
        """.format(st.session_state.get("opportunities", 0)), unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="summary-card">
            <div class="summary-card-icon">📈</div>
            <div class="summary-card-title">Trend Score</div>
            <div class="summary-card-value">{}</div>
            <div class="summary-card-desc">Overall trend strength</div>
        </div>
        """.format(f"{st.session_state.get('trend_score', 0):.1f}"), unsafe_allow_html=True)

def render_floating_panel():
    """Render the floating features panel"""
    if st.session_state.get("panel_open", False):
        st.markdown("### 🚀 All Features")
        # Feature buttons in columns
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Keyword Discovery", key="fp_kd", use_container_width=True):
                st.session_state.current_page = "keyword_discovery"
                st.rerun()
            if st.button("🧩 Competitor Gap", key="fp_cg", use_container_width=True):
                st.session_state.current_page = "competitor_gap"
                st.rerun()
            if st.button("🎯 Search Intent", key="fp_si", use_container_width=True):
                st.session_state.current_page = "search_intent"
                st.rerun()
            if st.button("🧠 Topic Clustering", key="fp_tc", use_container_width=True):
                st.session_state.current_page = "topic_clustering"
                st.rerun()
            if st.button("📈 Trend Forecasting", key="fp_tf", use_container_width=True):
                st.session_state.current_page = "trend_forecasting"
                st.rerun()
        with col2:
            if st.button("📰 SERP Analysis", key="fp_sa", use_container_width=True):
                st.session_state.current_page = "serp_analysis"
                st.rerun()
            if st.button("🧾 Content Optimization", key="fp_co", use_container_width=True):
                st.session_state.current_page = "content_optimization"
                st.rerun()
            if st.button("💰 Conversion Mapping", key="fp_cm", use_container_width=True):
                st.session_state.current_page = "conversion_mapping"
                st.rerun()
            if st.button("🌐 Industry Focus", key="fp_if", use_container_width=True):
                st.session_state.current_page = "industry_focus"
                st.rerun()
            if st.button("🧩 Full Strategy", key="fp_fs", use_container_width=True):
                st.session_state.current_page = "full_strategy"
                st.rerun()
            if st.button("🤖 Agent Mode", key="fp_am", use_container_width=True):
                st.session_state.current_page = "agent_mode"
                st.rerun()

