import streamlit as st
import base64
from sqlalchemy.orm import Session
from src.db_client import connect_db
from src.models import ResearchRunLog

def load_base64_image(path):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception:
        return ""

def render_landing_page():
    logo_base64 = load_base64_image("assets/keylytics_icon.png")

    st.markdown(f"""
    <div style="text-align: center; padding: 40px 20px;">
        <div style="margin-bottom: 20px;">
            <img src="data:image/png;base64,{logo_base64}" width="120" style="vertical-align:middle;" />
        </div>
        <h1 style="font-size: 4.5rem; font-weight: 700; color: #051B4A; margin-bottom: 10px; font-family: 'Cambria', serif;">Stratix</h1>
        <p style="font-size: 1.8rem; color: #232527; margin-bottom: 30px; font-family: 'Cambria', serif;">Where Autonomous Agents Turn Market Signals into Strategy</p>
        <p style="font-size: 1.2rem; color: #232527; max-width: 800px; margin: 0 auto 40px auto; line-height: 1.6; font-family: 'Cambria', serif;">
            Stratix automates comprehensive market intelligence research end-to-end. Powered by a stateful LangGraph orchestrator, Gemini LLMs, and high-fidelity search APIs, it turns raw keyword signals into executive intelligence reports with adversarial oversight.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Primary CTA
    col_l, col_btn, col_r = st.columns([2, 1, 2])
    with col_btn:
        if st.button("🚀 Launch Platform", type="primary", use_container_width=True, key="launch_platform_cta"):
            st.session_state.current_page = "home"
            st.rerun()

    st.markdown("<hr style='border: none; height: 1.5px; background: #051B4A; margin: 40px 0;' />", unsafe_allow_html=True)

    # 2. Graph Topology Visualization
    st.markdown("<h3 style='text-align: center; font-family: Cambria, serif;'>🤖 LangGraph Agent Pipeline Architecture</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; gap: 10px; flex-wrap: wrap; margin: 20px 0; padding: 20px; background-color: #FFFFFF; border-radius: 12px; border: 1.5px solid #051B4A; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
        <div style="padding: 10px; background-color: #CADEFF; border: 1.5px solid #051B4A; border-radius: 8px; font-weight: bold; color: #051B4A;">1. Planner Node</div>
        <div style="font-weight: bold; color: #051B4A;">➡</div>
        <div style="padding: 10px; background-color: #FFC7CF; border: 1.5px solid #051B4A; border-radius: 8px; font-weight: bold; color: #051B4A; text-align: center;">[HITL 1]<br/>Plan Approval</div>
        <div style="font-weight: bold; color: #051B4A;">➡</div>
        <div style="padding: 10px; background-color: #CADEFF; border: 1.5px solid #051B4A; border-radius: 8px; font-weight: bold; color: #051B4A;">2. Research Node</div>
        <div style="font-weight: bold; color: #051B4A;">➡</div>
        <div style="padding: 10px; background-color: #CADEFF; border: 1.5px solid #051B4A; border-radius: 8px; font-weight: bold; color: #051B4A;">3. Aggregator Node</div>
        <div style="font-weight: bold; color: #051B4A;">➡</div>
        <div style="padding: 10px; background-color: #CADEFF; border: 1.5px solid #051B4A; border-radius: 8px; font-weight: bold; color: #051B4A;">4. Quality Gate Node</div>
        <div style="font-weight: bold; color: #051B4A;">➡</div>
        <div style="padding: 10px; background-color: #CADEFF; border: 1.5px solid #051B4A; border-radius: 8px; font-weight: bold; color: #051B4A;">5. Critic Node</div>
        <div style="font-weight: bold; color: #051B4A;">➡</div>
        <div style="padding: 10px; background-color: #CADEFF; border: 1.5px solid #051B4A; border-radius: 8px; font-weight: bold; color: #051B4A;">6. Strategy Node</div>
        <div style="font-weight: bold; color: #051B4A;">➡</div>
        <div style="padding: 10px; background-color: #FFC7CF; border: 1.5px solid #051B4A; border-radius: 8px; font-weight: bold; color: #051B4A; text-align: center;">[HITL 2]<br/>Report Approval</div>
        <div style="font-weight: bold; color: #051B4A;">➡</div>
        <div style="padding: 10px; background-color: #6EE7B7; border: 1.5px solid #051B4A; border-radius: 8px; font-weight: bold; color: #051B4A;">7. Persist Node</div>
    </div>
    """, unsafe_allow_html=True)

    # 3. Why different callouts
    st.markdown("<h3 style='text-align: center; font-family: Cambria, serif;'>💡 Enterprise-Grade Capabilities</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="summary-card" style="height: 180px;">
            <div class="summary-card-title">🤖 Multi-Agent Orchestration</div>
            <div class="summary-card-desc">Specialized planner, researcher, aggregator, critic, and strategy nodes work in synergy to deliver complete strategies.</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="summary-card" style="height: 180px;">
            <div class="summary-card-title">🛡️ Adversarial Self-Critique</div>
            <div class="summary-card-desc">The Critic Node challenges findings for weak claims and missing information, prompting automatic retries before final synthesis.</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="summary-card" style="height: 180px;">
            <div class="summary-card-title">🔬 Human-in-the-Loop Gates</div>
            <div class="summary-card-desc">Stateful interrupts pause execution at planning and report stages, allowing operators to verify, edit, or reject progress.</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="summary-card" style="height: 180px;">
            <div class="summary-card-title">📊 LLM-as-Judge Evaluation</div>
            <div class="summary-card-desc">Every run undergoes systematic quality checks assessing plan coverage, report density, and search tool reliability.</div>
        </div>
        """, unsafe_allow_html=True)

def render_home_overview():
    logo_base64 = load_base64_image("assets/keylytics_icon.png")

    # Welcome section
    st.markdown(f"""
    <div style="width:100%; display:flex; justify-content:center;">
        <div class="home-container">
            <div class="welcome-section">
                <div class="app-logo" style="margin-bottom: -35px; margin-top: -150px;" >
                    <img src="data:image/png;base64,{logo_base64}" width="150" style="vertical-align:middle; margin:0; padding:0;" />
                </div>
                <h1 class="app-title">Stratix</h1>
                <p class="app-subtitle">Where Autonomous Agents Turn Market Signals into Strategy</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pipeline Status Section
    st.markdown("#### 🤖 Pipeline Status")
    status_data = {"active_runs": 0, "total_reports": 0, "active_jobs": 0}
    try:
        engine = connect_db()
        with Session(engine) as session:
            status_data["total_reports"] = session.query(ResearchRunLog).filter(
                ResearchRunLog.status == "completed"
            ).count()
            status_data["active_runs"] = session.query(ResearchRunLog).filter(
                ResearchRunLog.status.in_(["pending", "in_progress", "awaiting_approval"])
            ).count()
    except Exception:
        pass

    import requests
    import os
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    try:
        headers = {}
        api_key = os.getenv("STRATIX_API_KEY") or os.getenv("STRATIX_AI_API_KEY") or os.getenv("KEYLYTICS_API_KEY")
        if api_key:
            headers["X-API-Key"] = api_key
        jobs_resp = requests.get(f"{API_BASE_URL}/monitor/jobs", headers=headers, timeout=3)
        if jobs_resp.status_code == 200:
            status_data["active_jobs"] = len([j for j in jobs_resp.json() if j.get("status") == "active"])
    except Exception:
        pass

    from src.ui.components import render_card
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        render_card("Active Research Runs", str(status_data["active_runs"]), "Executing or awaiting approval", "🔬")
    with col_stat2:
        render_card("Total Intelligence Reports", str(status_data["total_reports"]), "Saved research reports", "📄")
    with col_stat3:
        render_card("Active Monitoring Jobs", str(status_data["active_jobs"]), "Scheduled tracking campaigns", "🕒")

    # Quick buttons
    st.markdown("### 🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🤖 Autonomous Research", use_container_width=True):
            st.session_state.current_page = "agent_mode"
            st.rerun()
    with col2:
        if st.button("📈 Executive Reports", use_container_width=True):
            st.session_state.current_page = "executive_reports"
            st.rerun()
    with col3:
        if st.button("📊 Unified Analytics", use_container_width=True):
            st.session_state.current_page = "analytics"
            st.rerun()

def render_floating_panel():
    """Render the floating features panel"""
    if st.session_state.get("panel_open", False):
        st.markdown("### 🚀 All Features")
        # Feature buttons in columns
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Keyword Discovery", key="fp_kd", use_container_width=True):
                st.session_state.panel_open = False
                st.session_state.current_page = "keyword_discovery"
                st.rerun()
            if st.button("🧩 Competitor Gap", key="fp_cg", use_container_width=True):
                st.session_state.panel_open = False
                st.session_state.current_page = "competitor_gap"
                st.rerun()
            if st.button("🧠 Topic Clustering", key="fp_tc", use_container_width=True):
                st.session_state.panel_open = False
                st.session_state.current_page = "topic_clustering"
                st.rerun()
            if st.button("📈 Trend Forecasting", key="fp_tf", use_container_width=True):
                st.session_state.panel_open = False
                st.session_state.current_page = "trend_forecasting"
                st.rerun()
        with col2:
            if st.button("📰 SERP Analysis", key="fp_sa", use_container_width=True):
                st.session_state.panel_open = False
                st.session_state.current_page = "serp_analysis"
                st.rerun()
            if st.button("🧩 Full Strategy", key="fp_fs", use_container_width=True):
                st.session_state.panel_open = False
                st.session_state.current_page = "full_strategy"
                st.rerun()

        st.write("")
        col_left, col_mid, col_right = st.columns([1, 2, 1])
        with col_mid:
            if st.button("🤖 Agent Mode", key="fp_am", use_container_width=True):
                st.session_state.panel_open = False
                st.session_state.current_page = "agent_mode"
                st.rerun()
