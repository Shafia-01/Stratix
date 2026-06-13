import streamlit as st

@st.cache_data(ttl=1800)
def cached_analyze_serp_opportunities(keyword):
    from src.serp_analyzer import analyze_serp_opportunities
    return analyze_serp_opportunities(keyword)
