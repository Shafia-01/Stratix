import streamlit as st
import pandas as pd
import plotly.express as px
from src.logger_config import get_logger
from src.services.keyword_service import (
    cached_run_lightweight_agent,
    cached_run_agent,
    prepare_keyword_records,
    cached_save_to_db
)
from src.services.metrics_service import update_global_metrics, increment_daily_requests, add_recent_search

logger = get_logger(__name__)

def render_keyword_discovery():
    """🔍 Keyword Discovery: Find, rank, and score keywords"""
    st.markdown("### 🔍 Keyword Discovery")
    st.markdown("Find, rank, and score keywords with comprehensive metrics and trend analysis.")
    # Input bar
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        keyword_input = st.text_input(
            "Enter a seed keyword or topic:",
            placeholder="e.g., 'AI tools', 'fitness apps', 'digital marketing'",
            key="keyword_discovery_input"
        )
    with col2:
        analysis_mode = st.selectbox(
            "Mode:",
            ["Quick (5)", "Standard (15)", "Full (30)", "Comprehensive (50)"],
            key="discovery_mode"
        )
    with col3:
        if st.button("🚀 Analyze", type="primary", use_container_width=True):
            if keyword_input:
                keyword_limit = {
                    "Quick (5)": 5,
                    "Standard (15)": 15,
                    "Full (30)": 30,
                    "Comprehensive (50)": 50
                }[analysis_mode]
                with st.spinner(f"Analyzing {keyword_limit} keywords..."):
                    try:
                        if keyword_limit <= 5:
                            results = cached_run_lightweight_agent(keyword_input, keyword_limit)
                        else:
                            results = cached_run_agent(keyword_input, keyword_limit)

                        # If results are fewer than requested, try to generate more
                        if results and len(results) > 0:
                            if len(results) < keyword_limit:
                                st.warning(f"⚠️ Only {len(results)} keywords were generated. This might be due to API limitations or caching.")
                                st.session_state.keyword_results = results
                            else:
                                st.session_state.keyword_results = results[:keyword_limit]

                            st.session_state.selected_keyword = keyword_input
                            st.session_state.keyword_results = prepare_keyword_records(
                                st.session_state.keyword_results,
                                keyword_input
                            )
                            # Update global metrics
                            update_global_metrics(st.session_state.keyword_results)
                            try:
                                cached_save_to_db(st.session_state.keyword_results)
                            except Exception as db_error:
                                st.warning(f"⚠️ Database save failed: {db_error}")
                            add_recent_search(keyword_input)
                            increment_daily_requests()
                            st.success(f"✅ Analyzed {len(st.session_state.keyword_results)} keywords!")
                        else:
                            st.error("❌ No keywords found. Please try a different term.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        import traceback
                        st.error(f"Details: {traceback.format_exc()}")
            else:
                st.warning("⚠️ Please enter a keyword first.")
    # Display results
    if "keyword_results" in st.session_state and st.session_state.keyword_results:
        results = st.session_state.keyword_results
        df = pd.DataFrame(results) if isinstance(results, list) else results

        # Remove problematic columns that show [object Object] or are not useful for display
        columns_to_remove = ['competitors', 'seed']
        display_columns = [col for col in df.columns if col not in columns_to_remove]
        df_display = df[display_columns].copy()

        # Metrics table
        st.markdown("#### 📊 Metrics Table")
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        # Trend graph
        if 'volume' in df.columns and 'score' in df.columns:
            st.markdown("#### 📈 Trend Graph")
            fig = px.scatter(
                df.head(20),
                x='volume',
                y='score',
                hover_data=['keyword', 'difficulty'],
                title="Volume vs Score Analysis",
                color='score',
                color_continuous_scale='Blues'
            )
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family="Inter", size=12)
            )
            st.plotly_chart(fig, use_container_width=True)

