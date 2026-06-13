import streamlit as st

@st.cache_data(ttl=1800)
def cached_analyze_competitor_gap(keyword):
    from src.competitor_gap_analyzer import analyze_competitor_keyword_gap
    return analyze_competitor_keyword_gap(keyword)
