import streamlit as st

def render_card(title: str, value: str = "", desc: str = "", icon: str = "", content_html: str = "", sidebar: bool = False):
    """Render a unified styled card component using the theme system."""
    icon_html = f"<div class='summary-card-icon' style='display: flex; align-items: center;'>{icon}</div>" if icon else ""
    value_html = f"<div class='summary-card-value' style='font-size: 1.8rem; font-weight: 700; color: #051B4A; margin-bottom: 8px;'>{value}</div>" if value else ""
    desc_html = f"<div class='summary-card-desc' style='font-size: 0.9rem; color: #232527; font-weight: 400; line-height: 1.5;'>{desc}</div>" if desc else ""
    inner_content = content_html if content_html else f"{value_html}{desc_html}"

    card_html = f"""
    <div class="summary-card" style="margin-bottom: 20px; text-align: left; background: #FFFFFF; border-radius: 12px; padding: 20px; border: 1.5px solid #051B4A; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); width: 100%; box-sizing: border-box;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
            {icon_html}
            <div class="summary-card-title" style="margin: 0; font-size: 1.05rem; font-weight: 600; color: #051B4A;">{title}</div>
        </div>
        {inner_content}
    </div>
    """
    if sidebar:
        st.sidebar.markdown(card_html, unsafe_allow_html=True)
    else:
        st.markdown(card_html, unsafe_allow_html=True)
