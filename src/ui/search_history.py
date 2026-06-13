import streamlit as st
from datetime import datetime
from src.services.keyword_service import cached_fetch_past_results

def render_search_history():
    st.markdown("### 📂 Search History")
    # Fetch from database (cached)
    with st.spinner("Loading search history..."):
        try:
            df_history = cached_fetch_past_results(limit=100)
            if not df_history.empty:
                st.success(f"✅ Loaded {len(df_history)} records from database")
                # Filters
                col1, col2, col3 = st.columns(3)
                with col1:
                    seed_filter = st.selectbox(
                        "Filter by Seed Keyword:",
                        ["All"] + list(df_history['seed'].unique())
                    )
                with col2:
                    difficulty_filter = st.selectbox(
                        "Filter by Difficulty:",
                        ["All", "Easy", "Medium", "Hard"]
                    )
                with col3:
                    volume_filter = st.slider(
                        "Minimum Volume:",
                        min_value=0,
                        max_value=int(df_history['volume'].max()) if 'volume' in df_history.columns else 1000,
                        value=0
                    )
                # Apply filters
                filtered_df = df_history.copy()
                if seed_filter != "All":
                    filtered_df = filtered_df[filtered_df['seed'] == seed_filter]
                if difficulty_filter != "All":
                    filtered_df = filtered_df[filtered_df['difficulty'].str.contains(difficulty_filter, na=False)]
                if 'volume' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['volume'] >= volume_filter]
                st.info(f"Showing {len(filtered_df)} filtered results")
                # Display filtered results
                if not filtered_df.empty:
                    # Style the dataframe
                    styled_df = filtered_df.style.map(
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
                    # Download button
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Filtered Results",
                        data=csv,
                        file_name=f"search_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No results match your filters")
            else:
                st.warning("No search history found. Try running some keyword analyses first.")
        except Exception as e:
            st.error(f"❌ Error loading history: {str(e)}")
            st.info("💡 Make sure your database is running and properly configured")
