import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
from dotenv import load_dotenv
from src.agent import run_agent
from src.db_client import fetch_past_results
from src.competitor_client import get_competitor_data

# ------------------------- SETUP -------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

st.set_page_config(page_title="GemKey AI", page_icon="💎", layout="wide")
st.title("💎 GemKey AI — Conversational SEO Research Assistant")

st.markdown(
    "Welcome to **GemKey AI**, your AI-powered SEO assistant 🤖\n\n"
    "Type a keyword or ask in natural language — for example:\n"
    "- `global internship`\n"
    "- `find low competition keywords for AI careers`\n"
    "- `generate blog ideas for eco-friendly fashion`\n"
    "- `explain keyword difficulty`\n\n"
    "GemKey AI will automatically detect your intent and respond intelligently!"
)

# ------------------------- CHAT STATE -------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ------------------------- HELPERS -------------------------
def detect_intent(user_input: str) -> str:
    """Use Gemini to detect what the user wants."""
    model = genai.GenerativeModel("gemini-2.5-flash")
    intent_prompt = f"""
    You are GemKey AI, an SEO assistant.
    Determine what the user wants to do from this message: "{user_input}"
    Choose one of:
      1. Generate Keywords
      2. Show SEO Trends
      3. Generate Content Ideas
      4. Explain SEO Concept
    """
    try:
        result = model.generate_content(intent_prompt)
        return result.text.strip().lower()
    except Exception as e:
        return f"error: {e}"

def highlight_difficulty(val):
    """Color-code difficulty cells."""
    color = ""
    if "Easy" in val:
        color = "#C6F6D5"   # light green
    elif "Medium" in val:
        color = "#FEF3C7"   # light yellow
    elif "Hard" in val:
        color = "#FECACA"   # light red
    return f"background-color: {color}"

def handle_intent(user_input: str, intent: str):
    """Route request to correct function."""
    # Case 1: Keyword Generation (or short seed)
    if "keyword" in intent or len(user_input.split()) <= 3:
        try:
            data = run_agent(user_input)
            if isinstance(data, pd.DataFrame) and not data.empty:
                summary = (
                    f"✅ **Found {len(data)} keyword ideas** related to "
                    f"**'{user_input}'**, ranked by SEO potential.\n\n"
                    f"Top suggestions:\n"
                    f"- {data.iloc[0]['keyword']}\n"
                    f"- {data.iloc[1]['keyword']}\n"
                    f"- {data.iloc[2]['keyword']}\n\n"
                    f"Here’s the table ↓"
                )
                
                # ---- Interactive Keyword Table with Competitor Buttons ----
                st.markdown("### 📊 Keyword Performance Overview")
                top_data = data.head(15)
                for idx, row in top_data.iterrows():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(
                            f"**{idx+1}. {row['keyword']}**  \n"
                            f"📈 Score: {row['score']} | 💰 CPC: {row['cpc']} | 🔍 Volume: {row['volume']}  \n"
                            f"{row['difficulty']} | {row['intent']} | 🔥 Trend: {row['trend']}"
                        )

                    with col2:
                        if st.button("View Competitors", key=f"comp_{idx}"):
                            competitors = get_competitor_data(row["keyword"])
                            if competitors:
                                st.markdown(f"#### 🕵️ Competitor Insights for: **{row['keyword']}**")
                                for comp in competitors:
                                    st.markdown(
                                        f"**{comp['rank']}. [{comp['title']}]({comp['link']})**  \n"
                                        f"🌐 {comp['domain']}  \n"
                                        f"📝 *{comp['snippet']}*"
                                    )
                            else:
                                st.warning(f"No competitor data found for '{row['keyword']}'.")

                    with col3:
                        st.write("")  # spacing
                        st.divider()
                
                # ---- COMPETITOR INSIGHTS ----
                top_kw = data.iloc[0]["keyword"]
                st.markdown("---")
                st.subheader(f"🕵️ Competitor Insights for: **{top_kw}**")
                
                competitors = get_competitor_data(top_kw)
                if competitors:
                    for comp in competitors:
                        st.markdown(
                            f"**{comp['rank']}. [{comp['title']}]({comp['link']})**  \n"
                            f"🌐 {comp['domain']}  \n"
                            f"📝 *{comp['snippet']}*"
                        )
                else:
                    st.warning(f"No competitor data found for '{top_kw}'.")

            else:
                return f"⚠️ No keywords generated for '{user_input}'.", None
        except Exception as e:
            return f"❌ Error generating keywords: {e}", None

    # Case 2: Trends
    elif "trend" in intent:
        from src.trend_client import get_trend_data
        
        top_keywords = ["AI jobs", "remote internships", "data science"]  # fallback example
        st.markdown(f"📈 Fetching Google Trends for top keywords related to '{user_input}'...")
        
        trend_df = get_trend_data(top_keywords[:5])
        if not trend_df.empty:
            st.line_chart(trend_df.set_index("date"))
            return "✅ Trend chart generated below.", None
        else:
            return f"⚠️ No trend data available for '{user_input}'.", None

    # Case 3: Content Ideas
    elif "content" in intent:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"Generate 3 catchy blog titles and 1 meta description for the topic '{user_input}'."
        try:
            result = model.generate_content(prompt)
            return f"🧠 Content Ideas:\n\n{result.text}", None
        except Exception as e:
            return f"Error generating content ideas: {e}", None

    # Case 4: SEO Explanation
    else:
        model = genai.GenerativeModel("gemini-2.5-flash")
        explain_prompt = f"Explain briefly the SEO concept: '{user_input}'."
        try:
            result = model.generate_content(explain_prompt)
            return result.text, None
        except Exception as e:
            return f"Error explaining concept: {e}", None

# ------------------------- MAIN CHAT LOOP -------------------------


st.markdown("---")
st.subheader("📂 View Past Keyword Searches")

if st.button("Show Previous Runs"):
    with st.spinner("Fetching past results..."):
        df_prev = fetch_past_results(limit=50)
        if not df_prev.empty:
            st.success(f"Showing the latest {len(df_prev)} results from database.")
            
            # Highlight difficulty colors
            def highlight_difficulty(val):
                color = ""
                if "Easy" in val:
                    color = "#C6F6D5"
                elif "Medium" in val:
                    color = "#FEF3C7"
                elif "Hard" in val:
                    color = "#FECACA"
                return f"background-color: {color}"
            
            styled_prev = df_prev.style.applymap(highlight_difficulty, subset=["difficulty"])
            st.dataframe(styled_prev, use_container_width=True)
        else:
            st.warning("No previous data found yet. Try running a keyword search first.")


prompt = st.chat_input("Type your query or keyword...")

if prompt:
    # Display user input
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # AI processing
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            intent = detect_intent(prompt)
            text_reply, styled_table = handle_intent(prompt, intent)

            # Show text response
            st.markdown(text_reply)

            # Show styled table if available
            if styled_table is not None:
                st.dataframe(styled_table, use_container_width=True)

    # Save AI response to chat memory
    st.session_state["messages"].append({"role": "assistant", "content": text_reply})

