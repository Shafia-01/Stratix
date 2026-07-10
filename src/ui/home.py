import streamlit as st
import base64
from sqlalchemy.orm import Session
from src.db_client import connect_db
from src.models import ResearchRunLog
from src.ui.theme import get_color_theme

def load_base64_image(path):
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception:
        return ""

def render_landing_page():
    colors = get_color_theme()
    logo_base64 = load_base64_image("assets/stratix_icon.png")

    _, center_col, _ = st.columns([1, 10, 1])
    with center_col:
        # Centered Hero block
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; text-align: center; padding: 10px 20px; gap: 8px;">
            <div style="height: auto; display: flex; align-items: center; justify-content: center; margin-bottom: 4px;">
                <img src="data:image/png;base64,{logo_base64}" height="120" style="object-fit: contain;" />
            </div>
            <h1 style="font-size: 3.5rem; font-weight: 700; color: #051B4A; margin: 0 0 4px 0; font-family: 'Cambria', serif; line-height: 1.0;">Stratix</h1>
            <p style="font-size: 1.6rem; color: #051B4A; margin: 0; font-family: 'Cambria', serif; font-weight: bold; font-style: italic;">Where Autonomous Agents Turn Market Signals into Strategy</p>
            <p style="font-size: 1.15rem; color: #000000; max-width: 800px; margin: 8px 0 0 0; line-height: 1.6;">
                Stratix automates comprehensive market intelligence research end-to-end. Powered by a stateful LangGraph orchestrator, Gemini LLMs, and high-fidelity search APIs, it turns raw keyword signals into executive intelligence reports with adversarial oversight.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Primary CTA
        col_l, col_btn, col_r = st.columns([2, 1.5, 2])
        with col_btn:
            if st.button("Launch Platform", type="primary", use_container_width=True, key="launch_platform_cta"):
                st.session_state.current_page = "home"
                st.rerun()

        st.markdown("<hr style='border: none; height: 1.5px; background: #051B4A; margin: 40px 0;' />", unsafe_allow_html=True)

        # Graph Topology Visualization
        st.markdown("<h3 style='text-align: center; font-family: Cambria, serif; font-size: 1.5rem; color: #051B4A;'>LangGraph Agent Pipeline Architecture</h3>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display: flex; justify-content: center; align-items: center; gap: 8px; flex-wrap: wrap; margin: 20px 0; padding: 20px; background-color: {colors['bg_card']}; border-radius: 12px; border: 1.5px solid {colors['border_dark']}; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <div style="padding: 8px 12px; background-color: {colors['node_agent']}; border: 1.5px solid {colors['border_dark']}; border-radius: 8px; font-weight: 500; font-size: 0.85rem; color: {colors['primary']}; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{colors['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg>
                1. Planner Node
            </div>
            <div style="font-weight: bold; color: {colors['primary']}; font-size: 1.1rem;">&rarr;</div>
            <div style="padding: 8px 12px; background-color: {colors['node_interrupt']}; border: 1.5px solid {colors['border_dark']}; border-radius: 8px; font-weight: 500; font-size: 0.85rem; color: {colors['primary']}; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{colors['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><polyline points="17 11 19 13 23 9"></polyline></svg>
                Plan Approval<br/><span style="font-size: 0.75rem; opacity: 0.85;">HITL 1</span>
            </div>
            <div style="font-weight: bold; color: {colors['primary']}; font-size: 1.1rem;">&rarr;</div>
            <div style="padding: 8px 12px; background-color: {colors['node_agent']}; border: 1.5px solid {colors['border_dark']}; border-radius: 8px; font-weight: 500; font-size: 0.85rem; color: {colors['primary']}; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{colors['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                2. Research Node
            </div>
            <div style="font-weight: bold; color: {colors['primary']}; font-size: 1.1rem;">&rarr;</div>
            <div style="padding: 8px 12px; background-color: {colors['node_agent']}; border: 1.5px solid {colors['border_dark']}; border-radius: 8px; font-weight: 500; font-size: 0.85rem; color: {colors['primary']}; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{colors['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path><polyline points="16 6 12 2 8 6"></polyline><line x1="12" y1="2" x2="12" y2="15"></line></svg>
                3. Aggregator Node
            </div>
            <div style="font-weight: bold; color: {colors['primary']}; font-size: 1.1rem;">&rarr;</div>
            <div style="padding: 8px 12px; background-color: {colors['node_agent']}; border: 1.5px solid {colors['border_dark']}; border-radius: 8px; font-weight: 500; font-size: 0.85rem; color: {colors['primary']}; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{colors['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                4. Quality Gate Node
            </div>
            <div style="font-weight: bold; color: {colors['primary']}; font-size: 1.1rem;">&rarr;</div>
            <div style="padding: 8px 12px; background-color: {colors['node_agent']}; border: 1.5px solid {colors['border_dark']}; border-radius: 8px; font-weight: 500; font-size: 0.85rem; color: {colors['primary']}; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{colors['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
                5. Critic Node
            </div>
            <div style="font-weight: bold; color: {colors['primary']}; font-size: 1.1rem;">&rarr;</div>
            <div style="padding: 8px 12px; background-color: {colors['node_agent']}; border: 1.5px solid {colors['border_dark']}; border-radius: 8px; font-weight: 500; font-size: 0.85rem; color: {colors['primary']}; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{colors['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>
                6. Strategy Node
            </div>
            <div style="font-weight: bold; color: {colors['primary']}; font-size: 1.1rem;">&rarr;</div>
            <div style="padding: 8px 12px; background-color: {colors['node_interrupt']}; border: 1.5px solid {colors['border_dark']}; border-radius: 8px; font-weight: 500; font-size: 0.85rem; color: {colors['primary']}; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{colors['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><polyline points="17 11 19 13 23 9"></polyline></svg>
                Report Approval<br/><span style="font-size: 0.75rem; opacity: 0.85;">HITL 2</span>
            </div>
            <div style="font-weight: bold; color: {colors['primary']}; font-size: 1.1rem;">&rarr;</div>
            <div style="padding: 8px 12px; background-color: {colors['node_terminal']}; border: 1.5px solid {colors['border_dark']}; border-radius: 8px; font-weight: 500; font-size: 0.85rem; color: {colors['primary']}; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{colors['primary']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
                7. Persist Node
            </div>
        </div>

        <div style="display: flex; justify-content: center; align-items: center; gap: 20px; font-size: 0.85rem; color: {colors['primary']}; margin-top: 10px; margin-bottom: 20px; flex-wrap: wrap;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: {colors['node_agent']}; border: 1px solid {colors['border_dark']};"></span>
                <span>Agent Node</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: {colors['node_interrupt']}; border: 1px solid {colors['border_dark']};"></span>
                <span>Human Approval Gate</span>
            </div>
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: {colors['node_terminal']}; border: 1px solid {colors['border_dark']};"></span>
                <span>Persistence</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<h3 style='text-align: center; font-family: Cambria, serif; font-size: 1.5rem; color: #051B4A; margin-top: 30px;'>Enterprise-Grade Capabilities</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            <div class="summary-card" style="min-height: 190px; height: auto; margin-bottom: 20px; background-color: #FFFFFF; border: 2px solid #051B4A; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; padding: 24px; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; margin-bottom: 12px; text-align: center; width: 100%;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#051B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="3" width="7" height="7" rx="1"></rect><rect x="14" y="14" width="7" height="7" rx="1"></rect><rect x="3" y="14" width="7" height="7" rx="1"></rect><path d="M10 6.5h4M10 17.5h4M6.5 10v4M17.5 10v4"></path></svg>
                    <div class="summary-card-title" style="margin: 0; font-size: 1.1rem; font-weight: 600; color: #051B4A; width: 100%;">Multi-Agent Orchestration</div>
                </div>
                <div class="summary-card-desc" style="font-size: 0.9rem; color: #000000; font-weight: 400; line-height: 1.5; text-align: center; width: 100%;">Specialized planner, researcher, aggregator, critic, and strategy nodes work in synergy to deliver complete strategies.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="summary-card" style="min-height: 190px; height: auto; margin-bottom: 20px; background-color: #FFFFFF; border: 2px solid #051B4A; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; padding: 24px; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; margin-bottom: 12px; text-align: center; width: 100%;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#051B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                    <div class="summary-card-title" style="margin: 0; font-size: 1.1rem; font-weight: 600; color: #051B4A; width: 100%;">Adversarial Self-Critique</div>
                </div>
                <div class="summary-card-desc" style="font-size: 0.9rem; color: #000000; font-weight: 400; line-height: 1.5; text-align: center; width: 100%;">The Critic Node challenges findings for weak claims and missing information, prompting automatic retries before final synthesis.</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown("""
            <div class="summary-card" style="min-height: 190px; height: auto; margin-bottom: 20px; background-color: #FFFFFF; border: 2px solid #051B4A; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; padding: 24px; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; margin-bottom: 12px; text-align: center; width: 100%;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#051B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                    <div class="summary-card-title" style="margin: 0; font-size: 1.1rem; font-weight: 600; color: #051B4A; width: 100%;">Human-in-the-Loop Gates</div>
                </div>
                <div class="summary-card-desc" style="font-size: 0.9rem; color: #000000; font-weight: 400; line-height: 1.5; text-align: center; width: 100%;">Stateful interrupts pause execution at planning and report stages, allowing operators to verify, edit, or reject progress.</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div class="summary-card" style="min-height: 190px; height: auto; margin-bottom: 20px; background-color: #FFFFFF; border: 2px solid #051B4A; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; padding: 24px; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                <div style="display: flex; flex-direction: column; align-items: center; gap: 8px; margin-bottom: 12px; text-align: center; width: 100%;">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#051B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
                    <div class="summary-card-title" style="margin: 0; font-size: 1.1rem; font-weight: 600; color: #051B4A; width: 100%;">LLM-as-Judge Evaluation</div>
                </div>
                <div class="summary-card-desc" style="font-size: 0.9rem; color: #000000; font-weight: 400; line-height: 1.5; text-align: center; width: 100%;">Every run undergoes systematic quality checks assessing plan coverage, report density, and search tool reliability.</div>
            </div>
            """, unsafe_allow_html=True)

def render_home_overview():
    logo_base64 = load_base64_image("assets/stratix_icon.png")

    # Welcome section
    st.markdown(f"""
    <div style="width:100%; display:flex; justify-content:center; padding: 10px 0;">
        <div class="home-container" style="max-width: 900px; width: 100%;">
            <div class="welcome-section" style="display: flex; flex-direction: column; align-items: center; text-align: center; gap: 8px;">
                <div class="app-logo" style="height: auto; display: flex; align-items: center; justify-content: center; margin-bottom: 4px;">
                    <img src="data:image/png;base64,{logo_base64}" height="140" style="object-fit: contain;" />
                </div>
                <h1 class="app-title" style="font-size: 3.5rem; font-weight: 700; color: #051B4A; margin: 0 0 4px 0;">Stratix</h1>
                <p class="app-subtitle" style="font-size: 1.5rem; color: #051B4A; margin: 0; font-weight: bold; font-style: italic;">Where Autonomous Agents Turn Market Signals into Strategy</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pipeline Status Section
    st.markdown('<h3 class="left-aligned-title">PIPELINE STATUS</h3>', unsafe_allow_html=True)
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
        render_card(
            title="Active Research Runs",
            value=str(status_data["active_runs"]),
            desc="Executing or awaiting approval",
            icon='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#051B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>'
        )
    with col_stat2:
        render_card(
            title="Total Intelligence Reports",
            value=str(status_data["total_reports"]),
            desc="Saved research reports",
            icon='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#051B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>'
        )
    with col_stat3:
        render_card(
            title="Active Monitoring Jobs",
            value=str(status_data["active_jobs"]),
            desc="Scheduled tracking campaigns",
            icon='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#051B4A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>'
        )

    # Quick buttons
    st.markdown('<h3 class="left-aligned-title">QUICK ACTIONS</h3>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Autonomous Research", use_container_width=True):
            st.session_state.current_page = "agent_mode"
            st.rerun()
    with col2:
        if st.button("Executive Reports", use_container_width=True):
            st.session_state.current_page = "executive_reports"
            st.rerun()
    with col3:
        if st.button("Unified Analytics", use_container_width=True):
            st.session_state.current_page = "analytics"
            st.rerun()
    with col4:
        if st.button("Intelligence Monitor", use_container_width=True):
            st.session_state.current_page = "monitoring_dashboard"
            st.rerun()
