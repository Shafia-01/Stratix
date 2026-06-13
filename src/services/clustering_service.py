import streamlit as st

@st.cache_data(ttl=1800)
def cached_cluster_keywords_semantically(keywords):
    from src.topic_clusterer import cluster_keywords_semantically
    return cluster_keywords_semantically(keywords)
