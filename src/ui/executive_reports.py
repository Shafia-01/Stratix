import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from src.db_client import connect_db
from src.models import ResearchRunLog
from src.graph.graph import get_compiled_graph

def render_executive_reports():
    st.title(" Executive Intelligence Workspace")
    st.markdown("Access comprehensive market intelligence reports synthesized by the multi-agent research pipeline.")

    # 1. Fetch completed runs from ResearchRunLog
    try:
        engine = connect_db()
        with Session(engine) as session:
            runs = session.query(ResearchRunLog).filter(ResearchRunLog.status == "completed").order_by(ResearchRunLog.completed_at.desc()).all()
    except Exception as e:
        st.error(f"Failed to fetch historical runs from database: {e}")
        return

    if not runs:
        st.info("No completed research runs found. Please run the Autonomous Research pipeline first.")
        return

    # Check if there is an active run we just completed
    run_options = {f"{r.seed_keyword} ({r.run_id[:8]}) - {r.completed_at}": r.run_id for r in runs}
    selected_label = st.selectbox("Select Intelligence Run:", list(run_options.keys()))
    selected_run_id = run_options[selected_label]

    # Fetch the state from the checkpointer
    try:
        graph = get_compiled_graph()
        config = {"configurable": {"thread_id": selected_run_id}}
        state = graph.get_state(config)
    except Exception as e:
        st.error(f"Failed to load execution state from checkpointer: {e}")
        return

    if not state or not state.values:
        st.error(f"Could not load state values for run `{selected_run_id}`.")
        return

    values = state.values
    report = values.get("strategy_report") or {}
    confidence = values.get("confidence_scores") or {}
    metadata = values.get("execution_metadata") or {}
    findings = values.get("intelligence_findings") or {}
    critic = values.get("critic_feedback") or {}

    # 2. Executive Summary
    st.markdown("### 📝 Executive Summary")
    st.info(report.get("executive_summary", "No executive summary generated."))

    # 3. Agent Confidence Breakdown
    st.markdown("###  Agent Confidence Breakdown")
    st.markdown("""
    > [!NOTE]
    > Confidence scores represent data quality, API coverage, and result density across research modules:
    > - **>= 80% (High Confidence)**: Excellent coverage with strong signals and low noise.
    > - **40% - 79% (Medium Confidence)**: Moderate density; recommendations are valid but require human verification.
    > - **< 40% (Low Confidence)**: Insufficient metrics or high API failure rates.
    """)
    if confidence:
        cols = st.columns(len(confidence))
        for idx, (module, score) in enumerate(confidence.items()):
            with cols[idx]:
                st.metric(label=module.replace("_", " ").title(), value=f"{score * 100:.0f}%")
                if score >= 0.8:
                    st.success("🟢 High Confidence")
                elif score >= 0.4:
                    st.warning("🟡 Medium Confidence")
                else:
                    st.error("🔴 Low Confidence")

    # 4. Competitive Landscape
    st.markdown("###  Competitive Landscape")
    comp_gap = findings.get("competitor_gap", {})
    if comp_gap and "opportunities" in comp_gap:
        opps_comp = comp_gap["opportunities"]
        if opps_comp:
            st.write("Identified competitor gaps and content opportunities:")
            df_comp = pd.DataFrame(opps_comp[:10])
            st.dataframe(df_comp, use_container_width=True)
        else:
            st.write("No significant competitor keyword gaps identified.")
    else:
        st.write("No competitor gap findings recorded in state.")

    # 5. Opportunities
    st.markdown("### 🎯 Strategic Opportunities")
    opps = report.get("top_opportunities", [])
    if opps:
        df_opps = pd.DataFrame(opps)
        display_cols = ["keyword", "volume", "difficulty", "intent", "score", "data_source"]
        existing_cols = [c for c in display_cols if c in df_opps.columns]
        st.dataframe(df_opps[existing_cols], use_container_width=True)
    else:
        st.write("No top opportunities mapped.")

    # 6. Risks & Data Limitations
    st.markdown("###  Risks & Data Limitations")
    limitations = findings.get("data_limitations", []) or []
    critic_gaps = critic.get("data_gaps", []) or []
    weak_claims = critic.get("weak_claims", []) or []

    all_risks = []
    if limitations:
        all_risks.extend([f"**Data Limitation:** {lim}" for lim in limitations])
    if critic_gaps:
        all_risks.extend([f"**Critic Identified Gap:** {gap}" for gap in critic_gaps])
    if weak_claims:
        all_risks.extend([f"**Weak Claim Challenge:** {claim}" for claim in weak_claims])

    if all_risks:
        for risk in all_risks:
            st.markdown(f"- {risk}")
    else:
        st.success("No significant data risks or limitations flagged for this run.")

    # 7. Strategic Recommendations
    st.markdown("###  Strategic Recommendations")
    recs = report.get("recommendations", [])
    if recs:
        for r in recs:
            st.markdown(f"- {r}")
    else:
        st.write("No recommendation items listed.")

    # 8. Decision Timeline
    st.markdown("###  Execution History & Decisions")
    st.markdown("View the complete sequence of agent nodes, tool invocations, and human checkpoints for this execution run.")
    if st.button("👁️ View Agent Timeline", use_container_width=True, key="view_agent_timeline_btn"):
        st.session_state.timeline_run_id = selected_run_id
        st.session_state.current_page = "agent_timeline"
        st.rerun()

    # 9. LangSmith Trace
    if metadata.get("langsmith_run_url"):
        st.markdown(f"🔗 [View full execution trace in LangSmith]({metadata['langsmith_run_url']})")

    # 10. Export Options
    st.markdown("### 📤 Export Report")
    md_content = f"# Executive Strategy Report: {selected_label}\n\n## 1. Executive Summary\n{report.get('executive_summary', 'N/A')}\n\n## 2. Confidence Breakdown\n"
    for m, score in confidence.items():
        md_content += f"- **{m.replace('_', ' ').title()}**: {score * 100:.0f}%\n"

    md_content += "\n## 3. Top Opportunities\n"
    for o in opps:
        md_content += f"- **{o.get('keyword', 'N/A')}** (Volume: {o.get('volume', 'N/A')}, Difficulty: {o.get('difficulty', 'N/A')}, Intent: {o.get('intent', 'N/A')}, Score: {o.get('score', 'N/A')})\n"

    md_content += "\n## 4. Risks & Data Limitations\n"
    if all_risks:
        for r in all_risks:
            md_content += f"- {r}\n"
    else:
        md_content += "- No significant data risks flagged.\n"

    md_content += "\n## 5. Recommendations\n"
    for r in recs:
        md_content += f"- {r}\n"

    st.download_button(
        label="📥 Download Report as Markdown",
        data=md_content,
        file_name=f"executive_report_{selected_run_id[:8]}.md",
        mime="text/markdown",
        key="download_executive_report"
    )
