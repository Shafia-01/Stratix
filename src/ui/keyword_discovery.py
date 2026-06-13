import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from src.logger_config import get_logger
from src.services.keyword_service import (
    cached_run_lightweight_agent,
    cached_run_agent,
    prepare_keyword_records,
    cached_save_to_db
)
from src.services.metrics_service import update_global_metrics, increment_daily_requests, add_recent_search

logger = get_logger(__name__)

def render_keyword_discovery():
    """🔍 Keyword Discovery: Find, rank, and score keywords"""
    st.markdown("### 🔍 Keyword Discovery")
    st.markdown("Find, rank, and score keywords with comprehensive metrics and trend analysis.")
    # Input bar
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        keyword_input = st.text_input(
            "Enter a seed keyword or topic:",
            placeholder="e.g., 'AI tools', 'fitness apps', 'digital marketing'",
            key="keyword_discovery_input"
        )
    with col2:
        analysis_mode = st.selectbox(
            "Mode:",
            ["Quick (5)", "Standard (15)", "Full (30)", "Comprehensive (50)"],
            key="discovery_mode"
        )
    with col3:
        if st.button("🚀 Analyze", type="primary", use_container_width=True):
            if keyword_input:
                keyword_limit = {
                    "Quick (5)": 5, 
                    "Standard (15)": 15, 
                    "Full (30)": 30,
                    "Comprehensive (50)": 50
                }[analysis_mode]
                with st.spinner(f"Analyzing {keyword_limit} keywords..."):
                    try:
                        if keyword_limit <= 5:
                            results = cached_run_lightweight_agent(keyword_input, keyword_limit)
                        else:
                            results = cached_run_agent(keyword_input, keyword_limit)
                        
                        # If results are fewer than requested, try to generate more
                        if results and len(results) > 0:
                            if len(results) < keyword_limit:
                                st.warning(f"⚠️ Only {len(results)} keywords were generated. This might be due to API limitations or caching.")
                                st.session_state.keyword_results = results
                            else:
                                st.session_state.keyword_results = results[:keyword_limit]
                            
                            st.session_state.selected_keyword = keyword_input
                            st.session_state.keyword_results = prepare_keyword_records(
                                st.session_state.keyword_results,
                                keyword_input
                            )
                            # Update global metrics
                            update_global_metrics(st.session_state.keyword_results)
                            try:
                                cached_save_to_db(st.session_state.keyword_results)
                            except Exception as db_error:
                                st.warning(f"⚠️ Database save failed: {db_error}")
                            add_recent_search(keyword_input)
                            increment_daily_requests()
                            st.success(f"✅ Analyzed {len(st.session_state.keyword_results)} keywords!")
                        else:
                            st.error("❌ No keywords found. Please try a different term.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        import traceback
                        st.error(f"Details: {traceback.format_exc()}")
            else:
                st.warning("⚠️ Please enter a keyword first.")   
    # Display results
    if "keyword_results" in st.session_state and st.session_state.keyword_results:
        results = st.session_state.keyword_results
        df = pd.DataFrame(results) if isinstance(results, list) else results
        
        # Remove problematic columns that show [object Object] or are not useful for display
        columns_to_remove = ['competitors', 'seed']
        display_columns = [col for col in df.columns if col not in columns_to_remove]
        df_display = df[display_columns].copy()
        
        # Metrics table
        st.markdown("#### 📊 Metrics Table")
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        # Trend graph
        if 'volume' in df.columns and 'score' in df.columns:
            st.markdown("#### 📈 Trend Graph")
            fig = px.scatter(
                df.head(20), 
                x='volume', 
                y='score',
                hover_data=['keyword', 'difficulty'],
                title="Volume vs Score Analysis",
                color='score',
                color_continuous_scale='Blues'
            )
            fig.update_layout(
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(family="Inter", size=12)
            )
            st.plotly_chart(fig, use_container_width=True)

def render_keyword_analysis():
    st.markdown("### 🔍 Keyword Analysis")
    # Add performance options
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        keyword_input = st.text_input(
            "Enter a seed keyword or topic:",
            placeholder="e.g., 'AI tools', 'fitness apps', 'digital marketing'",
            key="keyword_input"
        )    
    with col2:
        analysis_mode = st.selectbox(
            "Analysis Mode:",
            ["Quick (5 keywords)", "Standard (15 keywords)", "Full (30 keywords)", "Comprehensive (50 keywords)"],
            key="analysis_mode"
        )    
    with col3:
        if st.button("🚀 Analyze Keywords", type="primary", use_container_width=True):
            if keyword_input:
                # Determine keyword limit based on mode
                keyword_limit = {
                    "Quick (5 keywords)": 5, 
                    "Standard (15 keywords)": 15, 
                    "Full (30 keywords)": 30,
                    "Comprehensive (50 keywords)": 50
                }[analysis_mode]                
                with st.spinner(f"Analyzing {keyword_limit} keywords..."):
                    try:
                        # Use cached results if available
                        cache_key = f"keywords_{keyword_input}_{keyword_limit}"
                        if cache_key in st.session_state:
                            st.session_state.keyword_results = st.session_state[cache_key]
                            st.session_state.selected_keyword = keyword_input
                            st.success(f"✅ Loaded {len(st.session_state[cache_key])} cached keywords!")
                        else:
                            # Use lightweight agent for smaller sets, full agent for larger sets
                            if keyword_limit <= 5:
                                results = cached_run_lightweight_agent(keyword_input, keyword_limit)
                            else:
                                results = cached_run_agent(keyword_input, keyword_limit)                            
                            if results and len(results) > 0:
                                limited_results = results[:keyword_limit]
                                st.session_state.keyword_results = limited_results
                                st.session_state[cache_key] = limited_results  # Cache results
                                st.session_state.selected_keyword = keyword_input                                
                                # Save to database
                                try:
                                    prepared_results = prepare_keyword_records(limited_results, keyword_input)
                                    cached_save_to_db(prepared_results)
                                    st.success(f"✅ Analyzed {len(limited_results)} keywords and saved to database!")
                                except Exception as db_error:
                                    st.success(f"✅ Analyzed {len(limited_results)} keywords!")
                                    st.warning(f"⚠️ Database save failed: {db_error}")
                                add_recent_search(keyword_input)
                                increment_daily_requests()
                            else:
                                st.error("❌ No keywords found. Please try a different term.")
                    except Exception as e:
                        error_msg = str(e)
                        if "timeout" in error_msg.lower():
                            st.error("❌ Analysis timed out. Try 'Quick' mode or check your internet connection.")
                        elif "api" in error_msg.lower() or "key" in error_msg.lower():
                            st.error("❌ API error. Please check your GEMINI_API_KEY in the .env file.")
                        else:
                            st.error(f"❌ Error: {error_msg}")
            else:
                st.warning("⚠️ Please enter a keyword first.")    
    # Display results
    if "keyword_results" in st.session_state and st.session_state.keyword_results:
        results = st.session_state.keyword_results       
        # Convert to DataFrame if needed
        if isinstance(results, list):
            df = pd.DataFrame(results)
        else:
            df = results
        # Metrics Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-title">Total Keywords</div>
                <div class="metric-value">{}</div>
            </div>
            """.format(len(df)), unsafe_allow_html=True)
        with col2:
            avg_volume = df['volume'].mean() if 'volume' in df.columns else 0
            st.markdown("""
            <div class="metric-card">
                <div class="metric-title">Avg Volume</div>
                <div class="metric-value">{}</div>
            </div>
            """.format(f"{avg_volume:.0f}"), unsafe_allow_html=True)       
        with col3:
            avg_score = df['score'].mean() if 'score' in df.columns else 0
            st.markdown("""
            <div class="metric-card">
                <div class="metric-title">Avg Score</div>
                <div class="metric-value">{}</div>
            </div>
            """.format(f"{avg_score:.2f}"), unsafe_allow_html=True)
        with col4:
            easy_keywords = len(df[df['difficulty'].str.contains('Easy', na=False)]) if 'difficulty' in df.columns else 0
            st.markdown("""
            <div class="metric-card">
                <div class="metric-title">Easy Keywords</div>
                <div class="metric-value">{}</div>
            </div>
            """.format(easy_keywords), unsafe_allow_html=True)
        # Charts
        col1, col2 = st.columns(2)
        with col1:
            # Volume vs Score scatter plot
            if 'volume' in df.columns and 'score' in df.columns:
                fig = px.scatter(
                    df.head(20), 
                    x='volume', 
                    y='score',
                    hover_data=['keyword', 'difficulty'],
                    title="Volume vs Score Analysis",
                    color='score',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Inter", size=12)
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Difficulty distribution
            if 'difficulty' in df.columns:
                difficulty_counts = df['difficulty'].value_counts()
                fig = px.pie(
                    values=difficulty_counts.values,
                    names=difficulty_counts.index,
                    title="Difficulty Distribution",
                    color_discrete_sequence=['#10B981', '#F59E0B', '#EF4444']
                )
                fig.update_layout(
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    font=dict(family="Inter", size=12)
                )
                st.plotly_chart(fig, use_container_width=True)
        # Data Table
        st.markdown("### 📊 Keyword Results")
        
        # Remove problematic columns that show [object Object] or are not useful for display
        columns_to_remove = ['competitors', 'seed']
        display_columns = [col for col in df.columns if col not in columns_to_remove]
        df_display = df[display_columns].copy()
        
        # Style the dataframe
        if 'difficulty' in df_display.columns:
            styled_df = df_display.style.map(
                lambda x: 'background-color: #D1FAE5' if 'Easy' in str(x) else 
                         'background-color: #FEF3C7' if 'Medium' in str(x) else 
                         'background-color: #FEE2E2' if 'Hard' in str(x) else '',
                subset=['difficulty']
            )
            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            ) 
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"keywords_{st.session_state.selected_keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
