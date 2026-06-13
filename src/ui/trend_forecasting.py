import streamlit as st
import pandas as pd
import plotly.express as px
from src.services.keyword_service import cached_run_lightweight_agent
from src.services.trend_service import cached_analyze_trend_forecasting
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

def render_trend_forecasting_tab():
    st.markdown("### 📈 Trend Forecasting")
    col1, col2 = st.columns([2, 1])
    with col1:
        trend_keyword = st.text_input(
            "Enter keyword for trend analysis:",
            placeholder="e.g., 'AI tools', 'remote work'",
            key="trend_keyword"
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
        # Summary
        st.markdown("### 📋 Trend Summary")
        st.info(results.get("summary", "No summary available"))
        # Trend Analysis
        if "trend_analysis" in results and results["trend_analysis"]:
            st.markdown("### 📊 Trend Analysis")
            trend_data = []
            for keyword, analysis in results["trend_analysis"].items():
                trend_data.append({
                    "Keyword": keyword,
                    "Direction": analysis["direction"],
                    "Growth Rate": analysis["growth_rate"],
                    "Volatility": analysis["volatility"]
                })
            if trend_data:
                df_trends = pd.DataFrame(trend_data)
                fig = px.bar(
                    df_trends.head(10),
                    x="Keyword",
                    y="Growth Rate",
                    color="Direction",
                    title="Keyword Growth Rates",
                    color_discrete_map={
                        "strong_growth": "#10B981",
                        "moderate_growth": "#3B82F6",
                        "stable": "#6B7280",
                        "moderate_decline": "#F59E0B",
                        "strong_decline": "#EF4444"
                    }
                )
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Inter", size=12)
                )
                st.plotly_chart(fig, use_container_width=True)
        # Forecasts
        if "forecasts" in results and results["forecasts"]:
            st.markdown("### 🔮 6-Month Forecasts")
            for keyword, forecast in list(results["forecasts"].items())[:5]:
                with st.expander(f"📈 {keyword} - {forecast['trend_direction']}"):
                    st.markdown(f"**Predicted Growth:** {forecast['predicted_growth']}%")
                    st.markdown(f"**Recommendation:** {forecast['recommendation']}")
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
        # Seasonal Analysis
        if "seasonal_analysis" in results and results["seasonal_analysis"]:
            st.markdown("### 🗓️ Seasonal Patterns")
            for keyword, analysis in list(results["seasonal_analysis"].items())[:3]:
                with st.expander(f"📅 {keyword} - Seasonality: {analysis['seasonality_strength']}"):
                    st.markdown(f"**Peak Season:** Month {analysis['peak_season']}")
                    st.markdown(f"**Low Season:** Month {analysis['low_season']}")
                    st.markdown(f"**Recommendation:** {analysis['recommendation']}")
        # Insights
        if "insights" in results and results["insights"]:
            st.markdown("### 💡 Trend Insights")
            for insight in results["insights"]:
                st.markdown(f"**{insight['title']}**")
                st.markdown(insight['description'])
                st.markdown(f"*Recommendation:* {insight['recommendation']}")
                st.divider()
