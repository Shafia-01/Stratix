import streamlit as st
import pandas as pd
import plotly.express as px
from src.services.keyword_service import cached_run_lightweight_agent, prepare_keyword_records, cached_save_to_db
from src.services.clustering_service import cached_cluster_keywords_semantically

def render_topic_clustering():
    """🧠 Topic Clustering: Group related keywords"""
    st.markdown("### 🧠 Topic Clustering")
    st.markdown("Group related keywords into semantic clusters for better content strategy.")
    col1, col2 = st.columns([2, 1])
    with col1:
        cluster_keyword = st.text_input(
            "Enter seed keyword for clustering:",
            placeholder="e.g., 'AI tools', 'fitness apps'",
            key="cluster_keyword_new"
        )
    with col2:
        if st.button("🧠 Cluster Topics", type="primary", use_container_width=True):
            if cluster_keyword:
                with st.spinner("Clustering topics..."):
                    try:
                        keywords = cached_run_lightweight_agent(cluster_keyword, 15)
                        if keywords and len(keywords) > 0:
                            results = cached_cluster_keywords_semantically(keywords)
                            if results and "clusters" in results and len(results["clusters"]) > 0:
                                st.session_state.cluster_results = results
                                st.success(f"✅ Found {len(results['clusters'])} topic clusters!")
                            else:
                                st.warning("⚠️ No clusters found. Try a different keyword.")
                        else:
                            st.error("❌ No keywords found for clustering.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a keyword first.")
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

def render_topic_clustering_tab():
    st.markdown("### 🧩 Topic Clustering")
    col1, col2 = st.columns([2, 1])
    with col1:
        cluster_keyword = st.text_input(
            "Enter seed keyword for clustering:",
            placeholder="e.g., 'AI tools', 'fitness apps'",
            key="cluster_keyword"
        )
    with col2:
        if st.button("🧩 Cluster Topics", type="primary", use_container_width=True):
            if cluster_keyword:
                with st.spinner("Clustering topics..."):
                    try:
                        st.info("🔄 Generating keywords for clustering...")
                        keywords = cached_run_lightweight_agent(cluster_keyword, 10)
                        keywords = prepare_keyword_records(keywords, cluster_keyword)
                        if keywords and len(keywords) > 0:
                            st.info(f"✅ Generated {len(keywords)} keywords. Now clustering...")
                            try:
                                cached_save_to_db(keywords)
                                st.info("💾 Keywords saved to database")
                            except Exception as db_error:
                                st.warning(f"⚠️ Database save failed: {db_error}")
                            results = cached_cluster_keywords_semantically(keywords)
                            if results and "clusters" in results and len(results["clusters"]) > 0:
                                st.session_state.cluster_results = results
                                st.success(f"✅ Topic clustering complete! Found {len(results['clusters'])} clusters.")
                            else:
                                st.warning("⚠️ Clustering completed but no clusters found. Try a different keyword.")
                        else:
                            st.error("❌ No keywords found for clustering. Please try a different seed keyword.")
                    except Exception as e:
                        error_msg = str(e)
                        if "max() iterable argument is empty" in error_msg:
                            st.error("❌ Clustering failed: No data to cluster. Please try a different keyword or check your API connections.")
                        elif "api" in error_msg.lower() or "key" in error_msg.lower():
                            st.error("❌ API error. Please check your GEMINI_API_KEY in the .env file.")
                        else:
                            st.error(f"❌ Error: {error_msg}")
            else:
                st.warning("⚠️ Please enter a keyword first.")
    # Display results
    if "cluster_results" in st.session_state and st.session_state.cluster_results:
        results = st.session_state.cluster_results
        # Summary
        st.markdown("### 📋 Clustering Summary")
        st.info(results.get("summary", "No summary available"))
        # Clusters
        if "clusters" in results and results["clusters"]:
            st.markdown("### 🎯 Topic Clusters")
            for i, cluster in enumerate(results["clusters"]):
                with st.expander(f"#{i+1} {cluster['cluster_name']} ({cluster['keyword_count']} keywords)"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Description:** {cluster['description']}")
                        st.markdown(f"**Intent:** {cluster['primary_intent']}")
                        st.markdown(f"**Industry:** {cluster['industry_focus']}")
                        st.markdown(f"**Opportunity Score:** {cluster['opportunity_score']}")
                    with col2:
                        st.markdown("**Keywords:**")
                        for kw in cluster['keywords'][:10]:
                            st.markdown(f"- {kw}")
                    # Metrics
                    if "metrics" in cluster:
                        metrics = cluster["metrics"]
                        st.markdown("**Cluster Metrics:**")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Avg Volume", f"{metrics['avg_volume']:.0f}")
                        with col2:
                            st.metric("Avg Competition", f"{metrics['avg_competition']:.2f}")
                        with col3:
                            st.metric("Avg CPC", f"${metrics['avg_cpc']:.2f}")
                        with col4:
                            st.metric("Total Volume", f"{metrics['total_volume']:,}")
        # Insights
        if "insights" in results and results["insights"]:
            st.markdown("### 💡 Cluster Insights")
            for insight in results["insights"]:
                st.markdown(f"**{insight['title']}**")
                st.markdown(insight['description'])
                st.markdown(f"*Recommendation:* {insight['recommendation']}")
                st.divider()
