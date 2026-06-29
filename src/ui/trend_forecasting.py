import streamlit as st
import pandas as pd
import plotly.express as px
@st.cache_data(ttl=1800)
def cached_analyze_trend_forecasting(keywords):
    from src.trend_forecaster import analyze_trend_forecasting
    return analyze_trend_forecasting(keywords)

from src.services.keyword_service import cached_run_lightweight_agent
from src.services.metrics_service import increment_daily_requests, add_recent_search

def render_trend_forecasting():
    """📈 Trend Forecasting: Predict keyword trends"""
    st.markdown("### 📈 Trend Forecasting")
    st.markdown("Predict keyword trends with 6-month forecasts and seasonal analysis.")
    col1, col2 = st.columns([2, 1])
    with col1:
        trend_keyword = st.text_input(
            "Enter keyword for trend analysis:",
            placeholder="e.g., 'AI tools', 'remote work'",
            key="trend_keyword_new"
        )
    with col2:
        if st.button("📈 Forecast Trends", type="primary", use_container_width=True):
            if trend_keyword:
                with st.spinner("Analyzing trends..."):
                    try:
                        keywords = cached_run_lightweight_agent(trend_keyword, 8)
                        if keywords:
                            results = cached_analyze_trend_forecasting(keywords)
                            st.session_state.trend_results = results
                            add_recent_search(trend_keyword)
                            increment_daily_requests()
                            st.success("✅ Trend analysis complete!")
                        else:
                            st.error("❌ No keywords found for trend analysis.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a keyword first.")

    # Display results
    if "trend_results" in st.session_state and st.session_state.trend_results:
        results = st.session_state.trend_results
        # Line graph
        if "forecasts" in results and results["forecasts"]:
            st.markdown("#### 📊 Trend Forecasts")
            for keyword, forecast in list(results["forecasts"].items())[:3]:
                with st.expander(f"📈 {keyword} - {forecast['trend_direction']}"):
                    st.markdown(f"**Predicted Growth:** {forecast['predicted_growth']}%")
                    st.markdown(f"**Recommendation:** {forecast['recommendation']}")
                    # Forecast chart
                    if "forecast_scores" in forecast:
                        forecast_df = pd.DataFrame(forecast["forecast_scores"])
                        fig = px.line(
                            forecast_df,
                            x="month",
                            y="score",
                            title=f"6-Month Forecast: {keyword}",
                            markers=True
                        )
                        fig.update_layout(
                            plot_bgcolor='white',
                            paper_bgcolor='white',
                            font=dict(family="Inter", size=12)
                        )
                        st.plotly_chart(fig, use_container_width=True)
        # Seasonal peaks
        if "seasonal_analysis" in results and results["seasonal_analysis"]:
            st.markdown("#### 🗓️ Seasonal Peaks")
            for keyword, analysis in list(results["seasonal_analysis"].items())[:3]:
                growth_rate = analysis.get('growth_rate')
                growth_text = f"{growth_rate}%" if growth_rate is not None else "N/A"
                st.markdown(f"""
                **{keyword}**
                - Peak Season: Month {analysis['peak_season']}
                - Low Season: Month {analysis['low_season']}
                - Growth %: {growth_text}
                - Recommendation: {analysis['recommendation']}
                """)
                st.divider()

