import streamlit as st

def generate_chat_response(user_input):
    """Generate AI response based on user input."""
    try:
        user_lower = user_input.lower()
        if any(word in user_lower for word in ["keyword", "keywords", "search", "analyze"]):
            return f"🔍 **Keyword Analysis Ready!**\n\nI can help you analyze keywords for '{user_input}'. Here's what I can do:\n\n• **Generate related keywords** with search volume and competition data\n• **Analyze keyword difficulty** and scoring\n• **Find trending keywords** in your niche\n• **Suggest content ideas** based on keyword research\n\n💡 **Quick Start:** Use the 'Keyword Analysis' tab or ask me to 'find keywords for [your topic]'"        
        elif any(word in user_lower for word in ["trend", "trends", "forecast", "seasonal"]):
            return f"📈 **Trend Analysis Available!**\n\nI can help you understand trends for '{user_input}'. My capabilities include:\n\n• **6-month trend forecasts** with confidence scores\n• **Seasonal pattern analysis** to optimize content timing\n• **Growth rate calculations** and trend direction\n• **Market opportunity identification**\n\n💡 **Quick Start:** Use the 'Trend Forecasting' tab or ask me to 'analyze trends for [your topic]'"
        elif any(word in user_lower for word in ["competitor", "competitors", "gap", "opportunity"]):
            return f"🕵️ **Competitor Analysis Ready!**\n\nI can help you analyze competitors for '{user_input}'. Here's what I offer:\n\n• **Keyword gap analysis** to find missed opportunities\n• **Competitor ranking insights** and domain analysis\n• **Traffic potential scoring** for each opportunity\n• **Strategic recommendations** for outranking competitors\n\n💡 **Quick Start:** Use the 'Competitor Analysis' tab or ask me to 'find competitor gaps for [your keyword]'"
        elif any(word in user_lower for word in ["serp", "snippet", "optimization", "people also ask", "paa"]):
            return f"📊 **SERP Analysis Available!**\n\nI can help you optimize SERP performance for '{user_input}'. My features include:\n\n• **Snippet optimization opportunities** and recommendations\n• **People Also Ask (PAA) questions** extraction\n• **Title tag optimization** suggestions\n• **Content gap identification** in search results\n\n💡 **Quick Start:** Use the 'SERP Analysis' tab or ask me to 'analyze SERP for [your keyword]'"
        elif any(word in user_lower for word in ["cluster", "group", "topic", "semantic"]):
            return f"🧩 **Topic Clustering Ready!**\n\nI can help you cluster topics for '{user_input}'. Here's what I can do:\n\n• **Semantic keyword clustering** into meaningful groups\n• **Topic opportunity scoring** and prioritization\n• **Content strategy recommendations** by cluster\n• **Keyword relationship mapping** and insights\n\n💡 **Quick Start:** Use the 'Topic Clustering' tab or ask me to 'cluster topics for [your keyword]'"
        else:
            return f"💎 **Welcome to Keylytics!**\n\nI understand you're asking about '{user_input}'. I'm your comprehensive SEO research assistant with these powerful features:\n\n🔍 **Keyword Analysis** - Find and analyze keywords with metrics\n🕵️ **Competitor Analysis** - Discover keyword gaps and opportunities\n📊 **SERP Analysis** - Optimize snippets and find PAA questions\n🧩 **Topic Clustering** - Group keywords semantically\n📈 **Trend Forecasting** - Predict trends and seasonal patterns\n\n💡 **How to get started:**\n• Use the tabs above for detailed analysis\n• Ask me specific questions like 'find keywords for [topic]'\n• Try 'analyze competitors for [keyword]' for gap analysis\n• Use 'show trends for [keyword]' for forecasting\n\nWhat would you like to explore first?"
    except Exception as e:
        return f"⚠️ **I encountered an error:** {str(e)}\n\nPlease try again or use the specific tabs for detailed analysis. If the issue persists, check your API keys and internet connection."

def render_chat_interface():
    st.markdown("### 💬 Conversational SEO Assistant")
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    # Chat input
    if prompt := st.chat_input("Ask me anything about SEO, keywords, or trends..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Add to search history
        if prompt not in st.session_state.search_history:
            st.session_state.search_history.append(prompt)
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = generate_chat_response(prompt)
                st.markdown(response)
        # Add assistant message
        st.session_state.messages.append({"role": "assistant", "content": response})
