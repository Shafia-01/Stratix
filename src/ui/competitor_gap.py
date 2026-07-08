import streamlit as st
import pandas as pd
import plotly.express as px
@st.cache_data(ttl=1800)
def cached_analyze_competitor_gap(keyword):
    from src.competitor_gap_analyzer import analyze_competitor_keyword_gap
    return analyze_competitor_keyword_gap(keyword)

from src.services.metrics_service import increment_daily_requests, add_recent_search

def render_competitor_gap():
    """ Competitor Gap: Compare your keywords vs. competitors"""
    st.markdown("###  Competitor Gap Analysis")
    st.markdown("Compare your keywords against competitors to find missing opportunities.")
    col1, col2 = st.columns([2, 1])
    with col1:
        your_keyword = st.text_input(
            "Your keyword:",
            placeholder="e.g., 'project management software'",
            key="your_keyword"
        )
    with col2:
        competitor_keyword = st.text_input(
            "Competitor keyword:",
            placeholder="e.g., 'task management tools'",
            key="competitor_keyword"
        )
    if st.button(" Analyze Gap", type="primary"):
        if your_keyword and competitor_keyword:
            with st.spinner("Analyzing competitor gaps..."):
                try:
                    results = cached_analyze_competitor_gap(your_keyword)
                    if results and "error" not in results:
                        st.session_state.competitor_results = results
                        add_recent_search(your_keyword)
                        increment_daily_requests()
                        st.success(" Competitor analysis complete!")
                    else:
                        st.warning(" Analysis completed but no competitor data found.")
                except Exception as e:
                    st.error(f" Error: {str(e)}")
        else:
            st.warning(" Please enter both keywords.")
    # Display results
    if "competitor_results" in st.session_state and st.session_state.competitor_results:
        results = st.session_state.competitor_results
        if "opportunities" in results and results["opportunities"]:
            st.markdown("#### 🎯 Missing Keyword List")
            for i, opp in enumerate(results["opportunities"][:10]):
                with st.expander(f"#{i+1} {opp['keyword']} (Score: {opp['gap_score']})"):
                    st.markdown(f"**Opportunity Type:** {opp['opportunity_type']}")
                    st.markdown(f"**Traffic Potential:** {opp['traffic_potential']}")
                    st.markdown(f"**Reasoning:** {opp['reasoning']}")
        # Bar chart
        if "opportunities" in results and results["opportunities"]:
            st.markdown("####  Gap Analysis Chart")
            gap_data = []
            for opp in results["opportunities"][:10]:
                gap_data.append({
                    "Keyword": opp['keyword'][:20] + "...",
                    "Gap Score": opp['gap_score'],
                    "Traffic Potential": opp['traffic_potential']
                })
            if gap_data:
                df_gap = pd.DataFrame(gap_data)
                fig = px.bar(
                    df_gap,
                    x="Keyword",
                    y="Gap Score",
                    title="Top Keyword Gaps",
                    color="Gap Score",
                    color_continuous_scale="Reds"
                )
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Inter", size=12)
                )
                st.plotly_chart(fig, use_container_width=True)

