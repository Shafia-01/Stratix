"""
🤖 Agent Mode — Streamlit UI for the LangGraph autonomous research pipeline.

Provides a conversational-style interface for:
1. Entering a seed keyword
2. Reviewing and approving the AI-generated research plan
3. Monitoring research execution
4. Reviewing and approving the strategy report
5. Viewing the final results dashboard
"""
import requests
import streamlit as st
import pandas as pd
from src.logger_config import get_logger

logger = get_logger(__name__)

API_BASE = "http://localhost:8000"


def _post(endpoint: str, payload: dict) -> dict:
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to FastAPI server. Run: uvicorn api.main:app --reload --port 8000"}
    except Exception as e:
        return {"error": str(e)}


def _get(endpoint: str) -> dict:
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to FastAPI server."}
    except Exception as e:
        return {"error": str(e)}


def render_agent_mode():
    """🤖 Agent Mode: Autonomous multi-agent SEO research pipeline"""
    st.markdown("### 🤖 Agent Mode — Autonomous Research Pipeline")
    st.markdown(
        "Powered by **LangGraph** + **Gemini 2.5 Flash** + **6 Specialized Intelligence Tools**. "
        "The agent autonomously plans, researches, critiques, and synthesises market intelligence — "
        "with human approval at each critical decision point."
    )

    # ── Init session state ─────────────────────────────────────────────────
    if "agent_run_id" not in st.session_state:
        st.session_state.agent_run_id = None
    if "agent_stage" not in st.session_state:
        st.session_state.agent_stage = "input"  # input | plan_review | edit_plan | report_review | done
    if "agent_research_plan" not in st.session_state:
        st.session_state.agent_research_plan = None
    if "agent_strategy_report" not in st.session_state:
        st.session_state.agent_strategy_report = None
    if "agent_confidence" not in st.session_state:
        st.session_state.agent_confidence = None
    if "agent_warnings" not in st.session_state:
        st.session_state.agent_warnings = []

    stage = st.session_state.agent_stage

    # ── STAGE: Input ───────────────────────────────────────────────────────
    if stage == "input":
        col1, col2 = st.columns([3, 1])
        with col1:
            keyword = st.text_input(
                "Enter a seed keyword for autonomous research:",
                placeholder="e.g., 'AI SEO tools', 'project management software'",
                key="agent_keyword_input",
            )
        with col2:
            st.write("")  # spacing
            st.write("")
            if st.button("🚀 Start Agent", type="primary", use_container_width=True):
                if keyword:
                    with st.spinner("🧠 Planning research strategy..."):
                        result = _post("/agent/run", {"seed_keyword": keyword})
                    if "error" in result:
                        st.error(f"❌ {result['error']}")
                    else:
                        st.session_state.agent_run_id = result["run_id"]
                        st.session_state.agent_research_plan = (
                            result.get("checkpoint_data") or {}
                        ).get("research_plan")
                        st.session_state.agent_stage = "plan_review"
                        st.rerun()
                else:
                    st.warning("⚠️ Please enter a keyword first.")

    # ── STAGE: Plan Review (HITL Checkpoint 1) ─────────────────────────────
    elif stage == "plan_review":
        plan = st.session_state.agent_research_plan or {}
        run_id = st.session_state.agent_run_id

        st.markdown("#### 📋 AI-Generated Research Plan")
        st.info(
            "The AI has generated a research plan. Review it below, then approve "
            "to start data collection or edit before proceeding."
        )
        st.markdown(f"**Seed Keyword:** `{plan.get('seed_keyword', '')}`")
        st.markdown("**Objectives:**")
        for obj in plan.get("objectives", []):
            st.markdown(f"  - {obj}")
        st.markdown("**Modules to Run:**")
        for mod in plan.get("requested_modules", []):
            st.markdown(f"  - `{mod}`")
        st.markdown(f"**Max Keywords:** `{plan.get('max_keywords', 10)}`")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✅ Approve Plan", type="primary", use_container_width=True):
                with st.spinner("🔬 Running autonomous research (this may take 30-90 seconds)..."):
                    result = _post("/agent/resume", {
                        "run_id": run_id,
                        "human_feedback": {"approved": True},
                    })
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    status = result.get("status")
                    if status == "awaiting_approval":
                        cp = result.get("checkpoint_data") or {}
                        st.session_state.agent_strategy_report = cp.get("strategy_report")
                        st.session_state.agent_confidence = cp.get("confidence_scores")
                        st.session_state.agent_warnings = cp.get("warnings", [])
                        st.session_state.agent_stage = "report_review"
                    elif status == "completed":
                        st.session_state.agent_stage = "done"
                    else:
                        st.session_state.agent_stage = "done"
                    st.rerun()

        with col2:
            if st.button("✏️ Edit Plan", use_container_width=True):
                st.session_state.agent_stage = "edit_plan"
                st.rerun()

        with col3:
            if st.button("❌ Cancel Plan", use_container_width=True):
                st.session_state.agent_stage = "input"
                st.session_state.agent_run_id = None
                st.session_state.agent_research_plan = None
                st.rerun()

    # ── STAGE: Edit Plan ───────────────────────────────────────────────────
    elif stage == "edit_plan":
        plan = st.session_state.agent_research_plan or {}
        run_id = st.session_state.agent_run_id

        st.markdown("#### ✏️ Edit Research Plan")

        # Objectives input
        obj_text = "\n".join(plan.get("objectives", []))
        objectives_input = st.text_area(
            "Objectives (one per line):",
            value=obj_text,
            height=120
        )

        # Modules multi-select
        all_modules = [
            "keyword_discovery",
            "competitor_gap",
            "serp_analysis",
            "trend_forecasting",
            "topic_clustering"
        ]
        selected_modules = st.multiselect(
            "Requested Modules:",
            options=all_modules,
            default=plan.get("requested_modules", ["keyword_discovery"])
        )

        # Max keywords
        max_keywords_input = st.slider(
            "Max Keywords:",
            min_value=5,
            max_value=15,
            value=int(plan.get("max_keywords", 10))
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save & Approve Plan", type="primary", use_container_width=True):
                objectives_list = [line.strip() for line in objectives_input.split("\n") if line.strip()]
                edited_plan = {
                    "seed_keyword": plan.get("seed_keyword", ""),
                    "objectives": objectives_list,
                    "requested_modules": selected_modules,
                    "max_keywords": max_keywords_input
                }
                with st.spinner("🔬 Running autonomous research with updated plan (this may take 30-90 seconds)..."):
                    result = _post("/agent/resume", {
                        "run_id": run_id,
                        "human_feedback": {
                            "approved": True,
                            "edited_plan": edited_plan
                        }
                    })
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    status = result.get("status")
                    if status == "awaiting_approval":
                        cp = result.get("checkpoint_data") or {}
                        st.session_state.agent_strategy_report = cp.get("strategy_report")
                        st.session_state.agent_confidence = cp.get("confidence_scores")
                        st.session_state.agent_warnings = cp.get("warnings", [])
                        st.session_state.agent_stage = "report_review"
                    elif status == "completed":
                        st.session_state.agent_stage = "done"
                    else:
                        st.session_state.agent_stage = "done"
                    st.rerun()

        with col2:
            if st.button("🔙 Back", use_container_width=True):
                st.session_state.agent_stage = "plan_review"
                st.rerun()

    # ── STAGE: Report Review (HITL Checkpoint 2) ───────────────────────────
    elif stage == "report_review":
        report = st.session_state.agent_strategy_report or {}
        confidence = st.session_state.agent_confidence or {}
        warnings = st.session_state.agent_warnings or []
        run_id = st.session_state.agent_run_id

        st.markdown("#### 📋 AI-Generated Strategy Report")
        st.info("Please review the final strategy report before it is saved to the database.")

        if warnings:
            with st.expander("⚠️ Execution Warnings", expanded=False):
                for w in warnings:
                    st.warning(w)

        # Confidence scores
        st.markdown("##### 📊 Module Confidence Scores")
        cols = st.columns(len(confidence) if confidence else 1)
        for i, (module, score) in enumerate(confidence.items()):
            with cols[i % len(cols)]:
                st.metric(label=module.replace("_", " ").title(), value=f"{score * 100:.0f}%")

        # Executive Summary
        st.markdown("##### 📝 Executive Summary")
        st.markdown(report.get("executive_summary", "No summary generated."))

        # Recommendations
        st.markdown("##### 💡 Recommendations")
        for rec in report.get("recommendations", []):
            st.markdown(f"- {rec}")

        # Top Opportunities
        opps = report.get("top_opportunities", [])
        if opps:
            st.markdown("##### 📈 Top Opportunities")
            df = pd.DataFrame(opps)
            # Reorder columns for display
            display_cols = ["keyword", "volume", "difficulty", "intent", "score", "data_source"]
            existing_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[existing_cols], use_container_width=True)

        st.markdown("---")

        # HITL controls
        st.markdown("##### Feed back or Approve:")
        feedback_notes = st.text_area(
            "Enter notes for regeneration (optional):",
            placeholder="e.g., 'Focus more on transactional intent keywords', 'Avoid mentioning competitor X'"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Approve & Save", type="primary", use_container_width=True):
                with st.spinner("💾 Finalising and saving..."):
                    result = _post("/agent/resume", {
                        "run_id": run_id,
                        "human_feedback": {"approved": True}
                    })
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    st.session_state.agent_stage = "done"
                    st.rerun()

        with col2:
            if st.button("🔄 Request Regeneration", use_container_width=True):
                with st.spinner("🔄 Regenerating strategy report..."):
                    result = _post("/agent/resume", {
                        "run_id": run_id,
                        "human_feedback": {
                            "regenerate": True,
                            "notes": feedback_notes
                        }
                    })
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    status = result.get("status")
                    cp = result.get("checkpoint_data") or {}
                    st.session_state.agent_strategy_report = cp.get("strategy_report") or report
                    st.session_state.agent_confidence = cp.get("confidence_scores") or confidence
                    st.session_state.agent_warnings = cp.get("warnings", [])
                    st.session_state.agent_stage = "report_review"
                    st.rerun()

        with col3:
            if st.button("❌ Reject & Restart", use_container_width=True):
                st.session_state.agent_stage = "input"
                st.session_state.agent_run_id = None
                st.session_state.agent_research_plan = None
                st.session_state.agent_strategy_report = None
                st.session_state.agent_confidence = None
                st.rerun()

    # ── STAGE: Done ────────────────────────────────────────────────────────
    elif stage == "done":
        report = st.session_state.agent_strategy_report or {}
        st.balloons()
        st.success("🎉 Intelligence report successfully generated and persisted to the database.")

        st.markdown("##### 📝 Final Strategy Report Overview")
        st.markdown(report.get("executive_summary", ""))

        st.markdown("##### 💡 Core Recommendations")
        for rec in report.get("recommendations", []):
            st.markdown(f"- {rec}")

        st.markdown("---")
        if st.button("🔄 Start New Research", type="primary"):
            st.session_state.agent_stage = "input"
            st.session_state.agent_run_id = None
            st.session_state.agent_research_plan = None
            st.session_state.agent_strategy_report = None
            st.session_state.agent_confidence = None
            st.rerun()
