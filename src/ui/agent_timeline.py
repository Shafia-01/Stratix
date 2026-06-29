"""
Agent Execution Timeline — visual breakdown of a research run's node activations,
tool calls, HITL checkpoints, critic feedback, and quality scores.
"""
import streamlit as st
import requests
import os

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

NODE_ICONS = {
    "planner_node": "🧠",
    "research_agent_node": "🔬",
    "aggregator_node": "⚙️",
    "quality_gate_node": "🚪",
    "critic_node": "🔍",
    "strategy_agent_node": "📊",
    "persist_node": "💾",
}

EVENT_COLORS = {
    "node_start": "#4ADE80",
    "hitl_interrupt": "#FACC15",
    "tool_call": "#60A5FA",
    "error": "#F87171",
    "node_end": "#94A3B8",
}

def render_agent_timeline():
    st.markdown("### 🗂️ Agent Execution Timeline")
    st.markdown("Detailed breakdown of every decision, tool call, and quality check in the research pipeline.")

    run_id = st.text_input("Enter Run ID:", placeholder="Paste a run_id from an Agent Mode research run")

    if not run_id:
        st.info("Enter a Run ID from Agent Mode to view its execution timeline.")
        return

    if st.button("📊 Load Timeline", type="primary"):
        with st.spinner("Reconstructing execution timeline..."):
            try:
                headers = {}
                api_key = os.getenv("STRATIX_API_KEY") or os.getenv("STRATIX_AI_API_KEY") or os.getenv("KEYLYTICS_API_KEY")
                if api_key:
                    headers["X-API-Key"] = api_key
                resp = requests.get(f"{API_BASE}/timeline/{run_id}", headers=headers, timeout=30)
                if resp.status_code == 404:
                    st.error("Run not found. Check the Run ID and try again.")
                    return
                resp.raise_for_status()
                data = resp.json()
                st.session_state.timeline_data = data
            except Exception as e:
                st.error(f"Failed to load timeline: {e}")
                return

    if "timeline_data" not in st.session_state:
        return

    data = st.session_state.timeline_data

    # Header metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Status", data.get("status", "unknown").upper())
    with col2:
        st.metric("Keyword", data.get("seed_keyword", "—"))
    with col3:
        verdict = data.get("critic_verdict") or "—"
        st.metric("Critic Verdict", verdict)
    with col4:
        eval_scores = data.get("eval_scores", {})
        avg_eval = sum(eval_scores.values()) / len(eval_scores) if eval_scores else 0
        st.metric("Avg Eval Score", f"{avg_eval:.0%}")

    st.markdown("---")

    # Confidence scores
    confidence = data.get("confidence_scores", {})
    if confidence:
        st.markdown("#### 📊 Module Confidence Scores")
        conf_cols = st.columns(len(confidence))
        for i, (module, score) in enumerate(confidence.items()):
            color = "🟢" if score >= 0.7 else "🟡" if score >= 0.4 else "🔴"
            with conf_cols[i]:
                st.metric(
                    label=module.replace("_", " ").title(),
                    value=f"{score:.0%}",
                    delta=f"{color}"
                )

    # Eval scores
    if eval_scores:
        st.markdown("#### 🤖 LLM Evaluation Scores")
        eval_cols = st.columns(len(eval_scores))
        for i, (eval_type, score) in enumerate(eval_scores.items()):
            with eval_cols[i]:
                st.metric(
                    label=eval_type.replace("_", " ").title(),
                    value=f"{score:.0%}"
                )

    st.markdown("---")
    st.markdown("#### 🔄 Execution Events")

    events = data.get("events", [])

    # Separate node events from tool call events
    node_events = [e for e in events if e["event_type"] in ("node_start", "hitl_interrupt", "error")]
    tool_events = [e for e in events if e["event_type"] == "tool_call"]

    for event in node_events:
        node = event["node_name"]
        icon = NODE_ICONS.get(node, "⚙️")
        event_type = event["event_type"]

        if event_type == "hitl_interrupt":
            checkpoint = event.get("metadata", {}).get("checkpoint", "")
            st.warning(f"⏸️ **HUMAN APPROVAL REQUIRED** — `{checkpoint}`")
        elif event_type == "error":
            st.error(f"❌ Error in pipeline: {event.get('metadata', {}).get('error_message', 'Unknown error')}")
        else:
            with st.expander(f"{icon} {node.replace('_', ' ').title()}", expanded=False):
                meta = event.get("metadata", {})

                if node == "research_agent_node" and "tool_counts" in meta:
                    st.markdown("**Tools called:**")
                    for tool_name, count in meta["tool_counts"].items():
                        st.markdown(f"  - `{tool_name}`: {count} call(s)")

                if node == "aggregator_node" and "confidence_scores" in meta:
                    st.markdown("**Confidence computed:**")
                    for mod, score in meta["confidence_scores"].items():
                        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                        st.markdown(f"  - `{mod}`: {bar} {score:.0%}")

                if node == "critic_node" and "critic_feedback" in meta:
                    feedback = meta["critic_feedback"]
                    verdict = feedback.get("overall_verdict", "—")
                    st.markdown(f"**Verdict:** `{verdict}`")
                    if feedback.get("issues"):
                        st.markdown("**Issues identified:**")
                        for issue in feedback["issues"]:
                            st.markdown(f"  - {issue}")
                    if feedback.get("data_gaps"):
                        st.markdown("**Data gaps:**")
                        for gap in feedback["data_gaps"]:
                            st.markdown(f"  - {gap}")

                if not meta:
                    st.markdown("*Node executed successfully*")

    if tool_events:
        st.markdown("#### 🔧 Tool Call Details")
        for event in tool_events:
            meta = event.get("metadata", {})
            tool_name = meta.get("tool_name", "unknown")
            count = meta.get("call_count", 1)
            success = meta.get("success", True)
            status_icon = "✅" if success else "❌"
            st.markdown(f"{status_icon} `{tool_name}` — called {count} time(s)")
