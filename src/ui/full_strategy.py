import streamlit as st
import pandas as pd
from src.services.keyword_service import cached_run_lightweight_agent, prepare_keyword_records, cached_save_to_db
from src.services.metrics_service import update_global_metrics, increment_daily_requests, add_recent_search
from src.services.competitor_service import cached_analyze_competitor_gap
from src.services.clustering_service import cached_cluster_keywords_semantically
from src.services.trend_service import cached_analyze_trend_forecasting
from src.services.serp_service import cached_analyze_serp_opportunities

def render_full_strategy():
    """🧩 Full Strategy: Run all modules together"""
    st.markdown("### 🧩 Full Strategy Analysis")
    st.markdown("Run all modules together for comprehensive SEO strategy.")
    col1, col2 = st.columns([2, 1])
    with col1:
        strategy_keyword = st.text_input(
            "Enter main keyword for full strategy:",
            placeholder="e.g., 'project management software'",
            key="strategy_keyword"
        )
    with col2:
        if st.button("🧩 Run Full Strategy", type="primary", use_container_width=True):
            if strategy_keyword:
                with st.spinner("Running comprehensive analysis..."):
                    try:
                        progress_bar = st.progress(0)
                        # 1. Keyword Discovery
                        st.info("🔍 Running Keyword Discovery...")
                        keywords = cached_run_lightweight_agent(strategy_keyword, 20)
                        keywords = prepare_keyword_records(keywords, strategy_keyword)
                        if keywords:
                            try:
                                cached_save_to_db(keywords)
                            except Exception as db_error:
                                st.warning(f"⚠️ Keyword save skipped: {db_error}")
                            update_global_metrics(keywords)
                        progress_bar.progress(20)                       
                        # 2. Competitor Analysis
                        st.info("🧩 Running Competitor Gap Analysis...")
                        competitor_results = cached_analyze_competitor_gap(strategy_keyword)
                        progress_bar.progress(40)                       
                        # 3. Topic Clustering
                        st.info("🧠 Running Topic Clustering...")
                        cluster_results = cached_cluster_keywords_semantically(keywords) if keywords else None
                        progress_bar.progress(60)                       
                        # 4. Trend Forecasting
                        st.info("📈 Running Trend Forecasting...")
                        trend_results = cached_analyze_trend_forecasting(keywords) if keywords else None
                        progress_bar.progress(80)                       
                        # 5. SERP Analysis
                        st.info("📰 Running SERP Analysis...")
                        serp_results = cached_analyze_serp_opportunities(strategy_keyword)
                        progress_bar.progress(100)
                        # Store results
                        st.session_state.strategy_results = {
                            "keyword": strategy_keyword,
                            "keywords": keywords,
                            "competitor": competitor_results,
                            "clusters": cluster_results,
                            "trends": trend_results,
                            "serp": serp_results
                        }
                        add_recent_search(strategy_keyword)
                        increment_daily_requests()
                        st.success("✅ Full strategy analysis complete!")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a keyword first.")
    # Display results
    if "strategy_results" in st.session_state and st.session_state.strategy_results:
        results = st.session_state.strategy_results
        st.markdown("#### 📊 Comprehensive Strategy Dashboard")
        # Summary
        with st.expander("📋 Executive Summary", expanded=True):
            st.markdown(f"""
            **Keyword:** {results['keyword']}
            **Total Keywords Found:** {len(results['keywords']) if results['keywords'] else 0}
            **Competitor Opportunities:** {len(results['competitor'].get('opportunities', [])) if results['competitor'] and 'opportunities' in results['competitor'] else 0}
            **Topic Clusters:** {len(results['clusters'].get('clusters', [])) if results['clusters'] and 'clusters' in results['clusters'] else 0}
            **Trend Analysis:** {'✅ Complete' if results['trends'] else '❌ Failed'}
            **SERP Analysis:** {'✅ Complete' if results['serp'] else '❌ Failed'}
            """)
        # Keyword Discovery Results
        if results['keywords']:
            with st.expander("🔍 Keyword Discovery Results"):
                df = pd.DataFrame(results['keywords'])
                columns_to_remove = ['competitors', 'seed']
                display_columns = [col for col in df.columns if col not in columns_to_remove]
                df_display = df[display_columns].copy()
                st.dataframe(df_display.head(10), use_container_width=True, hide_index=True)
        # Competitor Gap Results
        if results['competitor'] and 'opportunities' in results['competitor']:
            with st.expander("🧩 Competitor Gap Opportunities"):
                for i, opp in enumerate(results['competitor']['opportunities'][:5]):
                    st.markdown(f"**{i+1}. {opp['keyword']}** - Score: {opp['gap_score']}")
        # Topic Clusters
        if Congressional_clusters := (results['clusters'] and 'clusters' in results['clusters']):
            with st.expander("🧠 Topic Clusters"):
                for i, cluster in enumerate(results['clusters']['clusters'][:3]):
                    st.markdown(f"**{i+1}. {cluster['cluster_name']}** ({cluster['keyword_count']} keywords)")
        # Trend Analysis
        if results['trends'] and 'forecasts' in results['trends']:
            with st.expander("📈 Trend Forecasts"):
                for keyword, forecast in list(results['trends']['forecasts'].items())[:3]:
                    st.markdown(f"**{keyword}:** {forecast['trend_direction']} ({forecast['predicted_growth']}%)")
        # SERP Analysis
        if results['serp'] and 'serp_data' in results['serp']:
            serp_data = results['serp'].get('serp_data', {})
            organic_results = serp_data.get('organic_results', []) if isinstance(serp_data, dict) else []
            with st.expander("📰 SERP Analysis"):
                st.markdown(f"**Top Results:** {len(organic_results)} pages analyzed")
                if organic_results:
                    st.markdown(f"**Top Result:** {organic_results[0].get('title', 'No title')}")
                else:
                    st.info("No organic SERP results available for this keyword.")
