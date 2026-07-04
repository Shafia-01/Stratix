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
import os
import json
from src.logger_config import get_logger

logger = get_logger(__name__)

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def _get_headers() -> dict:
    headers = {}
    api_key = os.getenv("STRATIX_API_KEY") or os.getenv("STRATIX_AI_API_KEY") or os.getenv("KEYLYTICS_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _post(endpoint: str, payload: dict) -> dict:
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=payload, headers=_get_headers(), timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to FastAPI server. Run: uvicorn api.main:app --reload --port 8000"}
    except Exception as e:
        return {"error": str(e)}


def _get(endpoint: str) -> dict:
    try:
        r = requests.get(f"{API_BASE}{endpoint}", headers=_get_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to FastAPI server."}
    except Exception as e:
        return {"error": str(e)}


def run_and_display_stream(payload: dict) -> dict:
    """Run the agent pipeline using SSE streaming and display live execution logs."""
    nodes = [
        "planner_node",
        "research_agent_node",
        "aggregator_node",
        "quality_gate_node",
        "critic_node",
        "strategy_agent_node",
        "persist_node"
    ]
    node_states = {n: "pending" for n in nodes}
    tool_calls = []
    confidence_scores = None
    critic_feedback = None
    errors = []
    run_id = None
    checkpoint_reached = None
    checkpoint_data = None
    completed = False

    status_placeholder = st.empty()
    progress_placeholder = st.empty()
    logs_placeholder = st.empty()
    metrics_placeholder = st.empty()
    critic_placeholder = st.empty()

    try:
        url = f"{API_BASE}/agent/stream"
        resp = requests.post(url, json=payload, headers=_get_headers(), stream=True, timeout=300)
        resp.raise_for_status()

        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8").strip()
            if not decoded.startswith("data: "):
                continue

            try:
                data = json.loads(decoded[6:])
            except Exception:
                continue

            event = data.get("event")
            if event == "run_started":
                run_id = data.get("run_id")
                st.session_state.agent_run_id = run_id
                status_placeholder.info(f"🚀 **Started Autonomous Execution Run:** `{run_id}`")
            elif event == "node_start":
                node = data.get("node")
                if node in node_states:
                    node_states[node] = "running"
            elif event == "node_complete":
                node = data.get("node")
                if node in node_states:
                    node_states[node] = "completed"
                if "confidence_scores" in data:
                    confidence_scores = data["confidence_scores"]
                if "critic_feedback" in data:
                    critic_feedback = data["critic_feedback"]
                if "errors" in data:
                    errors.extend(data["errors"])
            elif event == "tool_start":
                tool = data.get("tool")
                tool_calls.append({"tool": tool, "status": "running"})
            elif event == "tool_complete":
                tool = data.get("tool")
                success = data.get("success", True)
                for tc in reversed(tool_calls):
                    if tc["tool"] == tool and tc["status"] == "running":
                        tc["status"] = "success" if success else "failed"
                        break
            elif event == "checkpoint":
                checkpoint_reached = data.get("checkpoint")
                checkpoint_data = data.get("checkpoint_data")
            elif event == "completed":
                completed = True
            elif event == "error":
                st.error(f"❌ Pipeline error: {data.get('message')}")

            # Update UI
            with progress_placeholder.container():
                st.markdown("### 🔄 Graph Execution Progress")
                cols = st.columns(len(nodes))
                for idx, node in enumerate(nodes):
                    with cols[idx]:
                        state = node_states[node]
                        label = node.replace("_node", "").replace("_", " ").title()
                        if state == "pending":
                            st.markdown(f"⚪ **{label}**\n*(pending)*")
                        elif state == "running":
                            st.markdown(f"🔵 **{label}**\n*(running...)*")
                        elif state == "completed":
                            st.markdown(f"🟢 **{label}**\n*(complete)*")
                        else:
                            st.markdown(f"🔴 **{label}**\n*(failed)*")

            if tool_calls:
                with logs_placeholder.container():
                    st.markdown("#### 🛠️ Tool Execution Logs")
                    for tc in tool_calls:
                        t_label = tc["tool"].replace("_", " ").title()
                        if tc["status"] == "running":
                            st.info(f"⏳ Running tool: `{t_label}`...")
                        elif tc["status"] == "success":
                            st.success(f"✅ Tool `{t_label}` completed successfully.")
                        else:
                            st.error(f"❌ Tool `{t_label}` failed.")

            if confidence_scores:
                with metrics_placeholder.container():
                    st.markdown("#### 📊 Current Confidence Scores")
                    c_cols = st.columns(len(confidence_scores))
                    for c_idx, (m, score) in enumerate(confidence_scores.items()):
                        with c_cols[c_idx]:
                            st.metric(m.replace("_", " ").title(), f"{score * 100:.0f}%")

            if critic_feedback:
                with critic_placeholder.container():
                    st.markdown("#### 🛡️ Adversarial Critic Verdict")
                    verdict = critic_feedback.get("overall_verdict", "UNKNOWN")
                    if verdict == "PASS":
                        st.success("Verdict: **PASS**")
                    else:
                        st.warning("Verdict: **REVISE**")
                        issues = critic_feedback.get("issues", [])
                        if issues:
                            st.write(f"Reasoning: {issues[0] if isinstance(issues, list) else issues}")

    except Exception as e:
        st.error(f"❌ Connection to backend streaming failed: {e}")

    return {
        "run_id": run_id,
        "checkpoint": checkpoint_reached,
        "checkpoint_data": checkpoint_data,
        "completed": completed,
        "confidence_scores": confidence_scores,
        "critic_feedback": critic_feedback,
        "errors": errors
    }


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
                    result = run_and_display_stream({"seed_keyword": keyword})
                    if result.get("checkpoint") == "plan_approval":
                        st.session_state.agent_run_id = result["run_id"]
                        st.session_state.agent_research_plan = result.get("checkpoint_data", {}).get("research_plan")
                        st.session_state.agent_stage = "plan_review"
                        st.rerun()
                    elif result.get("completed"):
                        st.session_state.agent_stage = "done"
                        st.rerun()
                    else:
                        st.error("❌ Failed to complete agent run or reach checkpoint.")
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
                result = run_and_display_stream({
                    "run_id": run_id,
                    "human_feedback": {"approved": True},
                })
                if result.get("checkpoint") == "report_approval":
                    cp = result.get("checkpoint_data") or {}
                    st.session_state.agent_strategy_report = cp.get("strategy_report")
                    st.session_state.agent_confidence = cp.get("confidence_scores")
                    st.session_state.agent_warnings = cp.get("warnings", [])
                    st.session_state.agent_stage = "report_review"
                    st.rerun()
                elif result.get("completed"):
                    st.session_state.agent_stage = "done"
                    st.rerun()
                else:
                    st.error("❌ Failed to resume agent execution.")

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
                result = run_and_display_stream({
                    "run_id": run_id,
                    "human_feedback": {
                        "approved": True,
                        "edited_plan": edited_plan
                    }
                })
                if result.get("checkpoint") == "report_approval":
                    cp = result.get("checkpoint_data") or {}
                    st.session_state.agent_strategy_report = cp.get("strategy_report")
                    st.session_state.agent_confidence = cp.get("confidence_scores")
                    st.session_state.agent_warnings = cp.get("warnings", [])
                    st.session_state.agent_stage = "report_review"
                    st.rerun()
                elif result.get("completed"):
                    st.session_state.agent_stage = "done"
                    st.rerun()
                else:
                    st.error("❌ Failed to resume agent execution.")

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
                result = run_and_display_stream({
                    "run_id": run_id,
                    "human_feedback": {"approved": True}
                })
                if result.get("completed"):
                    st.session_state.agent_stage = "done"
                    st.rerun()
                else:
                    st.error("❌ Failed to complete agent run.")

        with col2:
            if st.button("🔄 Request Regeneration", use_container_width=True):
                result = run_and_display_stream({
                    "run_id": run_id,
                    "human_feedback": {
                        "regenerate": True,
                        "notes": feedback_notes
                    }
                })
                if result.get("checkpoint") == "report_approval":
                    cp = result.get("checkpoint_data") or {}
                    st.session_state.agent_strategy_report = cp.get("strategy_report") or report
                    st.session_state.agent_confidence = cp.get("confidence_scores") or confidence
                    st.session_state.agent_warnings = cp.get("warnings", [])
                    st.session_state.agent_stage = "report_review"
                    st.rerun()
                elif result.get("completed"):
                    st.session_state.agent_stage = "done"
                    st.rerun()
                else:
                    st.error("❌ Failed to resume agent execution.")

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
