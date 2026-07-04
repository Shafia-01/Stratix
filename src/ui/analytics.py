import streamlit as st
import requests
import os
from sqlalchemy.orm import Session
from src.db_client import connect_db
from src.models import ResearchRunLog
from src.graph.graph import get_compiled_graph

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

def _get_headers() -> dict:
    headers = {}
    api_key = os.getenv("STRATIX_API_KEY") or os.getenv("STRATIX_AI_API_KEY") or os.getenv("KEYLYTICS_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
    return headers

def render_analytics():
    st.title("📊 Unified Analytics & Observability Center")
    st.markdown("Monitor system-wide health, LLM-as-judge evaluation metrics, database statistics, and model tracing.")

    # 1. Fetch Health Detailed from API
    health_data = {}
    try:
        resp = requests.get(f"{API_BASE}/health/detailed", headers=_get_headers(), timeout=10)
        if resp.status_code == 200:
            health_data = resp.json()
        else:
            st.error("Failed to fetch detailed system health stats from API.")
    except Exception as e:
        st.error(f"API connection failed: {e}")

    # 2. Display Overview Metrics
    if health_data:
        st.markdown("### ⚙️ System Status")
        comp_cols = st.columns(len(health_data.get("components", {})))
        for idx, (comp, status) in enumerate(health_data.get("components", {}).items()):
            with comp_cols[idx]:
                label = comp.replace("_", " ").title()
                if status == "ok":
                    st.success(f"**{label}**\n\n🟢 Active")
                else:
                    st.error(f"**{label}**\n\n🔴 Degraded")

        # Database record counts & Evals
        st.markdown("### 📦 Database & Monitoring Statistics")
        db_stats = health_data.get("database", {})
        mon_stats = health_data.get("monitoring", {})
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Monitored Keywords", db_stats.get("keywords", 0))
        with col2:
            st.metric("Quality Evaluations Logs", db_stats.get("eval_results", 0))
        with col3:
            st.metric("Monitoring Jobs Scheduled", db_stats.get("monitoring_jobs", 0))
        with col4:
            st.metric("Active Cron Tasks", mon_stats.get("active_jobs", 0))

        # Average Quality Scores
        st.markdown("### 🤖 Average LLM-as-Judge Evaluator Scores")
        eval_scores = health_data.get("eval_scores", {})
        if eval_scores and "error" not in eval_scores:
            ev_cols = st.columns(len(eval_scores) if eval_scores else 1)
            for idx, (eval_type, avg_score) in enumerate(eval_scores.items()):
                with ev_cols[idx]:
                    if avg_score is not None:
                        st.metric(label=eval_type.replace("_", " ").title(), value=f"{avg_score * 100:.1f}%")
                    else:
                        st.metric(label=eval_type.replace("_", " ").title(), value="—")
        else:
            st.info("No LLM evaluation records found yet.")

    # 3. Fetch runs from DB for dropdown selection
    try:
        engine = connect_db()
        with Session(engine) as session:
            runs = session.query(ResearchRunLog).order_by(ResearchRunLog.started_at.desc()).all()
    except Exception as e:
        st.error(f"Failed to fetch runs: {e}")
        runs = []

    if runs:
        st.markdown("### 🔍 Run Deep-Dive & Execution Traces")

        # Calculate Critic PASS/REVISE rate across recent 10 runs from checkpointer
        st.markdown("#### 🛡️ Critic Verdict Rate (Last 10 Runs)")
        graph = get_compiled_graph()
        pass_count = 0
        revise_count = 0
        recent_runs_with_verdict = 0
        for r in runs[:10]:
            try:
                config = {"configurable": {"thread_id": r.run_id}}
                state = graph.get_state(config)
                if state and state.values:
                    critic = state.values.get("critic_feedback") or {}
                    verdict = critic.get("overall_verdict")
                    if verdict == "PASS":
                        pass_count += 1
                        recent_runs_with_verdict += 1
                    elif verdict == "REVISE":
                        revise_count += 1
                        recent_runs_with_verdict += 1
            except Exception:
                pass

        if recent_runs_with_verdict > 0:
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Critic PASS Count", pass_count)
            with c2:
                st.metric("Critic REVISE Count", revise_count)
        else:
            st.info("No critic feedback verdicts found in recent execution runs.")

        # Selector for timeline deep-linking
        run_options = {f"{r.seed_keyword} ({r.run_id[:8]}) - {r.started_at}": r.run_id for r in runs}
        selected_label = st.selectbox("Select Run to Inspect:", list(run_options.keys()), key="analytics_run_select")
        selected_run_id = run_options[selected_label]

        col1, col2 = st.columns(2)
        with col1:
            if st.button("👁️ View Execution Timeline", use_container_width=True, key="analytics_view_timeline"):
                st.session_state.timeline_run_id = selected_run_id
                st.session_state.current_page = "agent_timeline"
                st.rerun()

        # Render LangSmith Trace link if present
        try:
            config = {"configurable": {"thread_id": selected_run_id}}
            state = graph.get_state(config)
            if state and state.values:
                meta = state.values.get("execution_metadata") or {}
                langsmith_url = meta.get("langsmith_run_url")
                if langsmith_url:
                    with col2:
                        st.markdown(f"<a href='{langsmith_url}' target='_blank'><button style='width:100%; border:2px solid #051B4A; border-radius:8px; padding:8px 16px; font-weight:bold; background-color:#B5D1FF; color:#000;'>🛠️ View Trace in LangSmith</button></a>", unsafe_allow_html=True)
                else:
                    with col2:
                        st.info("No LangSmith trace URL linked for this run.")
        except Exception:
            pass
