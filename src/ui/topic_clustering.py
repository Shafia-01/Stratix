import streamlit as st
import pandas as pd
import plotly.express as px
@st.cache_data(ttl=1800)
def cached_cluster_keywords_semantically(keywords):
    from src.topic_clusterer import cluster_keywords_semantically
    return cluster_keywords_semantically(keywords)

from src.services.keyword_service import cached_run_lightweight_agent

def render_topic_clustering():
    """ Topic Clustering: Group related keywords"""
    st.markdown("###  Topic Clustering")
    st.markdown("Group related keywords into semantic clusters for better content strategy.")
    col1, col2 = st.columns([2, 1])
    with col1:
        cluster_keyword = st.text_input(
            "Enter seed keyword for clustering:",
            placeholder="e.g., 'AI tools', 'fitness apps'",
            key="cluster_keyword_new"
        )
    with col2:
        if st.button(" Cluster Topics", type="primary", use_container_width=True):
            if cluster_keyword:
                with st.spinner("Clustering topics..."):
                    try:
                        keywords = cached_run_lightweight_agent(cluster_keyword, 15)
                        if keywords and len(keywords) > 0:
                            results = cached_cluster_keywords_semantically(keywords)
                            if results and "clusters" in results and len(results["clusters"]) > 0:
                                st.session_state.cluster_results = results
                                st.success(f" Found {len(results['clusters'])} topic clusters!")
                            else:
                                st.warning(" No clusters found. Try a different keyword.")
                        else:
                            st.error(" No keywords found for clustering.")
                    except Exception as e:
                        st.error(f" Error: {str(e)}")
            else:
                st.warning(" Please enter a keyword first.")
    # Display results
    if "cluster_results" in st.session_state and st.session_state.cluster_results:
        results = st.session_state.cluster_results
        if "clusters" in results and results["clusters"]:
            st.markdown("#### 🎯 Topic Clusters")
            # Cluster visualization
            cluster_data = []
            for i, cluster in enumerate(results["clusters"]):
                cluster_data.append({
                    "Cluster": f"Cluster {i+1}",
                    "Keywords": cluster['keyword_count'],
                    "Opportunity Score": cluster['opportunity_score']
                })
            if cluster_data:
                df_clusters = pd.DataFrame(cluster_data)
                fig = px.bar(
                    df_clusters,
                    x="Cluster",
                    y="Opportunity Score",
                    title="Cluster Opportunity Scores",
                    color="Opportunity Score",
                    color_continuous_scale="Viridis"
                )
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Inter", size=12)
                )
                st.plotly_chart(fig, use_container_width=True)
            # Grouped tables
            for i, cluster in enumerate(results["clusters"]):
                with st.expander(f"#{i+1} {cluster['cluster_name']} ({cluster['keyword_count']} keywords)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Description:** {cluster['description']}")
                        st.markdown(f"**Intent:** {cluster['primary_intent']}")
                        st.markdown(f"**Industry:** {cluster['industry_focus']}")
                    with col2:
                        st.markdown("**Keywords:**")
                        for kw in cluster['keywords'][:8]:
                            st.markdown(f"- {kw}")

