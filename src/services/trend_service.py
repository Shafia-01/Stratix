import streamlit as st

@st.cache_data(ttl=1800)
def cached_analyze_trend_forecasting(keywords):
    from src.trend_forecaster import analyze_trend_forecasting
    return analyze_trend_forecasting(keywords)
