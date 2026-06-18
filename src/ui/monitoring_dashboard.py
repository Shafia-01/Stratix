import streamlit as st
import requests
import os
import pandas as pd
import plotly.express as px

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def render_monitoring_dashboard():
    st.title("🛡️ Intelligence Monitoring & Quality Analytics Center")
    st.markdown("Track keyword performance shifts over time, manage recurring monitoring schedules, and view LLM-as-judge evaluation analytics.")

    tabs = st.tabs(["🕒 Automated Intelligence Jobs", "📊 Intelligence Report History", "🤖 Quality Evaluation Analytics"])

    # ---------------------------------------------------------
    # TAB 1: Monitoring Schedules
    # ---------------------------------------------------------
    with tabs[0]:
        st.header("🕒 Active Monitoring Jobs")

        # Form to add a new job
        with st.expander("➕ Create New Monitoring Job", expanded=False):
            with st.form("create_job_form"):
                seed_keyword = st.text_input("Seed Keyword", placeholder="e.g. organic coffee")
                interval_hours = st.number_input("Interval (Hours)", min_value=1, value=24, step=1)

                submitted = st.form_submit_button("Schedule Job")
                if submitted:
                    if not seed_keyword.strip():
                        st.error("Please enter a seed keyword.")
                    else:
                        try:
                            resp = requests.post(f"{API_BASE_URL}/monitor/add", json={
                                "seed_keyword": seed_keyword.strip(),
                                "interval_hours": interval_hours
                            })
                            if resp.status_code == 200:
                                st.success(f"Successfully scheduled monitoring for '{seed_keyword}' every {interval_hours} hours!")
                                st.rerun()
                            else:
                                st.error(f"Failed to create job: {resp.text}")
                        except Exception as e:
                            st.error(f"Error connecting to backend: {e}")

        # Fetch and list existing jobs
        try:
            resp = requests.get(f"{API_BASE_URL}/monitor/jobs")
            if resp.status_code == 200:
                jobs = resp.json()
                if jobs:
                    for job in jobs:
                        with st.container():
                            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                            with col1:
                                st.markdown(f"**Seed:** `{job['seed_keyword']}`")
                            with col2:
                                st.markdown(f"**Interval:** {job.get('interval_hours', job.get('interval_minutes', 'N/A'))} hrs")
                            with col3:
                                st.markdown(f"**Next Run:** {job.get('next_run_time') or 'N/A'}")
                            with col4:
                                if st.button("🗑️", key=f"del_job_{job['job_id']}", help="Delete monitoring job"):
                                    del_resp = requests.delete(f"{API_BASE_URL}/monitor/{job['job_id']}")
                                    if del_resp.status_code == 200:
                                        st.success("Deleted job")
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete job")
                            st.markdown("---")
                else:
                    st.info("No active monitoring jobs scheduled.")
            else:
                st.error("Could not fetch active monitoring jobs from API.")
        except Exception as e:
            st.error(f"Backend API connection failed: {e}")

    # ---------------------------------------------------------
    # TAB 2: Historical Runs & Diffs
    # ---------------------------------------------------------
    with tabs[1]:
        st.header("📊 Historical Runs & Strategy Report Diffs")

        # 1. Fetch search history / monitored runs
        try:
            jobs_resp = requests.get(f"{API_BASE_URL}/monitor/jobs")
            if jobs_resp.status_code == 200:
                jobs = jobs_resp.json()
                if not jobs:
                    st.info("No active monitoring jobs. Add one in the 'Monitoring Schedules' tab first.")
                else:
                    unique_keywords = list(set(j['seed_keyword'] for j in jobs))
                    selected_seed = st.selectbox("Select Monitored Keyword", unique_keywords)

                    hist_resp = requests.get(f"{API_BASE_URL}/monitor/history/{selected_seed}")
                    if hist_resp.status_code == 200:
                        history = hist_resp.json()
                        if not history:
                            st.info("No monitoring execution runs found yet for this keyword.")
                        else:
                            df_hist = pd.DataFrame(history)
                            time_col = "started_at" if "started_at" in df_hist.columns else ("created_at" if "created_at" in df_hist.columns else df_hist.columns[0])
                            filtered_runs = df_hist.sort_values(by=time_col, ascending=False)

                            display_cols = [col for col in ["run_id", "started_at", "status"] if col in filtered_runs.columns]
                            st.dataframe(filtered_runs[display_cols], use_container_width=True)

                            # Diff comparison selection
                            st.subheader("🔍 Compare Consecutive Strategy Reports")
                            if len(filtered_runs) < 2:
                                st.info("At least 2 runs are required to compute a report difference.")
                            else:
                                run_options = {f"{r[time_col]} ({r['run_id'][:8]})": r["run_id"] for _, r in filtered_runs.iterrows()}

                                col1, col2 = st.columns(2)
                                with col1:
                                    newer_run_label = st.selectbox("Newer Run (A)", list(run_options.keys()), index=0)
                                with col2:
                                    older_run_label = st.selectbox("Older Run (B)", list(run_options.keys()), index=min(1, len(run_options)-1))

                                newer_run_id = run_options[newer_run_label]
                                older_run_id = run_options[older_run_label]

                                if newer_run_id == older_run_id:
                                    st.warning("Please select two different runs to compare.")
                                elif st.button("Compute Report Diff"):
                                    try:
                                        diff_resp = requests.get(f"{API_BASE_URL}/monitor/diff", params={
                                            "newer_run_id": newer_run_id,
                                            "older_run_id": older_run_id
                                        })
                                        if diff_resp.status_code == 200:
                                            diff_data = diff_resp.json()

                                            st.success("Diff generated successfully!")
                                            st.markdown("### 📝 Diff Summary: A vs B")
                                            st.info(diff_data.get("summary") or "No changes detected.")

                                            # Confidence deltas
                                            st.markdown("#### ⚖️ Confidence score shifts")
                                            conf_deltas = diff_data.get("confidence_deltas") or {}
                                            if conf_deltas:
                                                c_cols = st.columns(len(conf_deltas))
                                                for idx, (module, delta) in enumerate(conf_deltas.items()):
                                                    with c_cols[idx]:
                                                        st.metric(label=f"{module} shift", value=f"{delta:+.2f}")

                                            # Keyword score shifts
                                            st.markdown("#### 🔑 Keyword Score Deltas")
                                            kw_deltas = diff_data.get("keyword_score_deltas") or []
                                            if kw_deltas:
                                                df_kw = pd.DataFrame(kw_deltas)
                                                st.dataframe(df_kw, use_container_width=True)
                                            else:
                                                st.write("No matching keyword score deltas found.")

                                            # Added/Dropped Recommendations
                                            col_add, col_drop = st.columns(2)
                                            with col_add:
                                                st.markdown("#### ➕ Added Recommendations")
                                                added_recs = diff_data.get("added_recommendations") or []
                                                if added_recs:
                                                    for r in added_recs:
                                                        st.markdown(f"- {r}")
                                                else:
                                                    st.write("*None*")

                                            with col_drop:
                                                st.markdown("#### ➖ Dropped Recommendations")
                                                dropped_recs = diff_data.get("dropped_recommendations") or []
                                                if dropped_recs:
                                                    for r in dropped_recs:
                                                        st.markdown(f"- {r}")
                                                else:
                                                    st.write("*None*")
                                        else:
                                            st.error(f"Failed to fetch diff: {diff_resp.text}")
                                    except Exception as e:
                                        st.error(f"Error computing diff: {e}")
            else:
                st.error("Failed to fetch monitored history from API.")
        except Exception as e:
            st.error(f"Backend API connection failed: {e}")

    # ---------------------------------------------------------
    # TAB 3: LLM Evaluation Analytics
    # ---------------------------------------------------------
    with tabs[2]:
        st.header("🤖 LLM-As-Judge Quality Evaluations")
        st.markdown("Analytics and trends on plan quality, strategy report quality, and tool execution reliability.")

        try:
            # Let user search keyword trends using active jobs
            jobs_resp = requests.get(f"{API_BASE_URL}/monitor/jobs")
            if jobs_resp.status_code == 200:
                jobs = jobs_resp.json()
                if jobs:
                    unique_keywords = list(set(job["seed_keyword"] for job in jobs))
                    selected_trend_seed = st.selectbox("Select Keyword to Track Score Trends", unique_keywords, key="trend_seed_select")

                    # Fetch trends
                    trends_resp = requests.get(f"{API_BASE_URL}/evals/trends/{selected_trend_seed}")
                    if trends_resp.status_code == 200:
                        trends = trends_resp.json()
                        if not trends:
                            st.info(f"No LLM evaluation runs recorded for '{selected_trend_seed}' yet.")
                        else:
                            df_trends = pd.DataFrame(trends)

                            # Interactive line chart of evaluation scores
                            st.subheader("📈 Quality Metric Trends (Last 10 Runs)")

                            fig = px.line(
                                df_trends,
                                x="run_id",
                                y=["plan_score", "report_score", "tool_score"],
                                labels={"value": "Score (0.0 - 1.0)", "run_id": "Research Run ID"},
                                title=f"LLM-as-Judge Trend Lines for '{selected_trend_seed}'",
                                markers=True
                            )
                            fig.update_layout(yaxis_range=[0, 1.1])
                            st.plotly_chart(fig, use_container_width=True)

                            # Detailed eval reports
                            st.subheader("📋 Evaluation Run Log Details")
                            for run_eval in trends:
                                with st.expander(f"Run ID: {run_eval['run_id'][:12]} — Date: {run_eval.get('evaluated_at', 'Unknown')}"):
                                    st.markdown(f"**Plan Score:** `{run_eval['plan_score']:.2f}`")
                                    st.markdown(f"**Report Score:** `{run_eval['report_score']:.2f}`")
                                    st.markdown(f"**Tool Reliability Score:** `{run_eval['tool_score']:.2f}`")
                                    st.markdown(f"**Evaluated At:** {run_eval['evaluated_at']}")
                else:
                    st.info("No active monitoring jobs found.")
            else:
                st.error("Failed to load active monitoring jobs for evaluation analytics.")
        except Exception as e:
            st.error(f"Backend API connection failed: {e}")
