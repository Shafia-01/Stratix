import streamlit as st

def render_card(title: str, value: str, desc: str = "", icon: str = ""):
    """Render a unified styled card component using the theme system."""
    icon_html = f"<div class='summary-card-icon'>{icon}</div>" if icon else ""
    desc_html = f"<div class='summary-card-desc'>{desc}</div>" if desc else ""
    st.markdown(f"""
    <div class="summary-card" style="height: auto; margin-bottom: 20px; text-align: center; background: #FFFFFF; border-radius: 16px; padding: 24px; border: 1.5px solid #051B4A; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
        {icon_html}
        <div class="summary-card-title" style="font-family: 'Cambria', serif; font-size: 1.1rem; font-weight: bold; color: #232527; margin-bottom: 8px;">{title}</div>
        <div class="summary-card-value" style="font-family: 'Cambria', serif; font-size: 2rem; font-weight: 700; color: #2563EB; margin-bottom: 8px;">{value}</div>
        {desc_html}
    </div>
    """, unsafe_allow_html=True)
