import streamlit as st
import pandas as pd
import plotly.express as px
from src.services.keyword_service import cached_run_lightweight_agent

def render_conversion_mapping():
    """💰 Conversion Mapping: Rank by CPC, buyer intent"""
    st.markdown("### 💰 Conversion Mapping")
    st.markdown("Rank keywords by CPC and buyer intent for maximum ROI.")
    # Get keyword data
    if "keyword_results" in st.session_state and st.session_state.keyword_results:
        df = pd.DataFrame(st.session_state.keyword_results)

        # Remove problematic columns
        columns_to_remove = ['competitors', 'seed']
        display_columns = [col for col in df.columns if col not in columns_to_remove]
        df_clean = df[display_columns].copy()

        if 'cpc' in df_clean.columns and 'score' in df_clean.columns:
            # Calculate ROI potential
            df_clean['roi_potential'] = df_clean['score'] / (df_clean['cpc'] + 0.01)  # Avoid division by zero
            # Sort by ROI potential
            df_sorted = df_clean.sort_values('roi_potential', ascending=False)
            st.markdown("#### 📊 ROI Potential Ranking")
            # Table sorted by ROI potential - show only relevant columns
            conversion_cols = ['keyword', 'volume', 'cpc', 'score', 'roi_potential']
            available_cols = [col for col in conversion_cols if col in df_sorted.columns]
            st.dataframe(
                df_sorted[available_cols].head(20),
                use_container_width=True,
                hide_index=True
            )
            # ROI chart
            fig = px.bar(
                df_sorted.head(15),
                x="keyword",
                y="roi_potential",
                title="Top Keywords by ROI Potential",
                color="roi_potential",
                color_continuous_scale="Greens"
            )
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family="Inter", size=12),
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ CPC data not available. Run keyword analysis first.")
    else:
        st.info("💡 Run keyword analysis first to see conversion mapping data.")
        # Quick keyword input for conversion analysis
        quick_keyword = st.text_input(
            "Enter keyword for quick conversion analysis:",
            placeholder="e.g., 'buy project management software'",
            key="conversion_keyword"
        )
        if st.button("💰 Analyze Conversion", type="primary"):
            if quick_keyword:
                with st.spinner("Analyzing conversion potential..."):
                    try:
                        keywords = cached_run_lightweight_agent(quick_keyword, 10)
                        if keywords:
                            df = pd.DataFrame(keywords)
                            # Remove problematic columns
                            columns_to_remove = ['competitors', 'seed']
                            display_columns = [col for col in df.columns if col not in columns_to_remove]
                            df_clean = df[display_columns].copy()

                            if 'cpc' in df_clean.columns and 'score' in df_clean.columns:
                                df_clean['roi_potential'] = df_clean['score'] / (df_clean['cpc'] + 0.01)
                                df_sorted = df_clean.sort_values('roi_potential', ascending=False)
                                st.markdown("#### 📊 Conversion Analysis Results")
                                # Show only relevant columns for conversion mapping
                                conversion_cols = ['keyword', 'volume', 'cpc', 'score', 'roi_potential']
                                available_cols = [col for col in conversion_cols if col in df_sorted.columns]
                                st.dataframe(
                                    df_sorted[available_cols],
                                    use_container_width=True,
                                    hide_index=True
                                )
                            else:
                                st.warning("⚠️ CPC data not available for this keyword.")
                        else:
                            st.error("❌ No keywords found.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
