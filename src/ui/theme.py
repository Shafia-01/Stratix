import streamlit as st

def get_color_theme():
    """Get light theme colors."""
    return {
        "primary": "#051B4A",
        "primary_hover": "#CADEFF",
        "primary_light": "#B5D1FF",
        "secondary": "#6EE7B7",
        "secondary_hover": "#34D399",
        "bg_main": "#FFF7ED",
        "bg_card": "#FFFFFF",
        "bg_sidebar": "#FFC7CF",
        "text_primary": "#000000",
        "text_secondary": "#232527",
        "text_white": "#FFFFFF",
        "border_light": "#000000",
        "border_dark": "#051B4A",
        "success": "#4ADE80",
        "warning": "#FACC15",
        "error": "#F87171",
        "info": "#60A5FA"
    }

def get_optimized_css():
    """Get optimized CSS with light theme colors."""
    colors = get_color_theme()
    return f"""
    <style>
    /* Import Cambria font and Material Icons */
    @import url('https://fonts.googleapis.com/css2?family=Cambria:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');
    /* Global Styles */
    .main {{
        background-color: {colors['bg_main']} !important;
        font-family: 'Cambria', serif !important;
    }}

    /* Force theme colors on main containers */
    .stApp {{
        background-color: {colors['bg_main']} !important;
    }}

    div[data-testid="stAppViewContainer"] {{
        background-color: {colors['bg_main']} !important;
    }}
    /* Apply Cambria only to specific text elements, NOT buttons or icons */
    body, p, div.stMarkdown, div.stText, h1, h2, h3, h4, h5, h6,
    label, input, textarea, select, option {{
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
    }}
    /* DO NOT apply Cambria to buttons, icons, or navigation */
    button, [data-testid="stSidebarNav"], [data-testid="stSidebarNav"] * {{
        font-family: inherit !important;
    }}
    /* Apply Cambria only to text content, NOT interactive elements */
    .stMarkdown, .stText, .stTitle, .stHeader, .stSubheader {{
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
    }}
    /* DO NOT override buttons, inputs, or interactive elements */
    .stButton, .stButton > button, .stSelectbox, .stTextInput, .stTextArea {{
        font-family: inherit !important;
    }}
    /* Apply Cambria only to text content in sidebar */
    .stSidebar .stMarkdown, .stSidebar .stText {{
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
    }}
    /* Sidebar Styling */
    .css-1d391kg {{
        background-color: {colors['bg_sidebar']} !important;
        border-right: 2px solid {colors['border_light']};
    }}

    /* Force sidebar background */
    section[data-testid="stSidebar"] {{
        background-color: {colors['bg_sidebar']} !important;
    }}

    div[data-testid="stSidebar"] {{
        background-color: {colors['bg_sidebar']} !important;
    }}
    .css-1d391kg .css-1v0mbdj {{
        color: {colors['text_primary']};
        font-family: 'Cambria', serif;
        font-weight: bold;
    }}
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: {colors['bg_card']};
        border-radius: 8px;
        padding: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {colors['bg_main']};
        border-radius: 6px;
        padding: 8px 16px;
        font-family: 'Cambria', serif;
        font-weight: 500;
        color: {colors['text_secondary']};
        transition: all 0.3s ease;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {colors['primary']};
        color: {colors['text_white']};
        box-shadow: 0 2px 8px {colors['primary']}30;
    }}
    /* Card Styling */
    .metric-card {{
        background-color: {colors['bg_card']};
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1.5px solid {colors['border_light']};
        margin: 10px 0;
    }}
    .metric-title {{
        font-family: 'Cambria', serif;
        font-size: 14px;
        font-weight: 500;
        color: {colors['text_secondary']};
        margin-bottom: 8px;
    }}
    .metric-value {{
        font-family: 'Cambria', serif;
        font-size: 24px;
        font-weight: 600;
        color: {colors['primary']};
    }}
    /* Chat Styling */
    .chat-container {{
        background-color: {colors['bg_card']};
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1.5px solid {colors['border_light']};
        margin: 10px 0;
    }}
    .chat-message {{
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
        font-family: 'Cambria', serif;
    }}
    .chat-user {{
        background-color: {colors['primary']};
        color: {colors['text_white']};
        margin-left: 20%;
    }}
    .chat-assistant {{
        background-color: {colors['bg_main']};
        color: {colors['text_primary']};
        margin-right: 20%;
    }}
    /* Button Styling */
    .stButton > button {{
        background-color: {colors['primary']};
        color: {colors['text_white']};
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-family: 'Cambria', serif;
        font-weight: 500;
        transition: all 0.3s ease;
    }}
    .stButton > button:hover {{
        background-color: {colors['primary_hover']};
        box-shadow: 0 4px 8px {colors['primary']}30;
    }}
    /* Chart Styling */
    .plotly-chart {{
        background-color: {colors['bg_card']};
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1.5px solid {colors['border_light']};
    }}
    /* Table Styling */
    .stDataFrame {{
        background-color: {colors['bg_card']};
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1.5px solid {colors['border_light']};
    }}
    /* Header Styling */
    .main-header {{
        background: linear-gradient(135deg, {colors['primary']} 0%, {colors['primary_hover']} 100%);
        color: {colors['text_white']};
        padding: 30px;
        border-radius: 16px;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 8px 16px {colors['primary']}30;
    }}
    .main-header h1 {{
        font-family: 'Cambria', serif;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .main-header p {{
        font-family: 'Cambria', serif;
        font-size: 1.1rem;
        margin: 10px 0 0 0;
        opacity: 0.9;
    }}
    /* Sidebar Header */
    .sidebar-header {{
        background: linear-gradient(135deg, {colors['primary']} 0%, {colors['primary_hover']} 100%);
        color: {colors['text_white']};
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
    }}
    .sidebar-header h2 {{
        font-family: 'Cambria', serif;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
    }}
    /* Success/Error Messages */
    .stSuccess {{
        background-color: #D1FAE5;
        border: 1px solid #10B981;
        color: #065F46;
        border-radius: 8px;
    }}
    .stError {{
        background-color: #FEE2E2;
        border: 1px solid #EF4444;
        color: #991B1B;
        border-radius: 8px;
    }}
    .stWarning {{
        background-color: #FEF3C7;
        border: 1px solid #F59E0B;
        color: #92400E;
        border-radius: 8px;
    }}
    /* Loading Spinner */
    .stSpinner {{
        color: #2563EB;
    }}
    /* Download Button */
    .download-btn {{
        background-color: #FFC7CF;
        color: #000000;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
    }}
    .download-btn:hover {{
        background-color: #FFB3C1;
        box-shadow: 0 4px 8px rgba(255, 199, 207, 0.3);
    }}
    /* Streamlit Download Button Styling */
    .stDownloadButton button {{
        background-color: #FFC7CF !important;
        color: #000000 !important;
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }}
    .stDownloadButton button:hover {{
        background-color: #B5D1FF !important;
        box-shadow: 0 4px 8px rgba(255, 199, 207, 0.3) !important;
    }}
    .stDownloadButton button:active {{
        background-color: #FFC7CF !important;
        border: 2px solid #051B4A !important;
    }}
    /* All Streamlit Buttons Border Styling */
    .stButton button {{
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }}
    /* Sidebar Buttons */
    .stSidebar .stButton button {{
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
        font-family: 'Cambria', serif !important;
        font-weight: bold !important;
        }}
        /* Primary Buttons */
    .stButton > button:first-child {{
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
    }}
    /* Secondary Buttons */
    .stButton > button:nth-child(2) {{
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
    }}
    /* Floating Panel Styles */
    .floating-panel {{
        position: fixed;
        top: 20px;
        right: -400px;
        width: 380px;
        height: calc(100vh - 40px);
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
        border-radius: 16px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
        border: 1px solid #E5E7EB;
        transition: right 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 1000;
        overflow-y: auto;
        padding: 20px;
    }}
    .floating-panel.open {{
        right: 20px;
    }}
    .floating-toggle {{
        position: fixed;
        top: 50%;
        right: 20px;
        transform: translateY(-50%);
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        border: none;
        border-radius: 50px 0 0 50px;
        padding: 15px 20px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3);
        transition: all 0.3s ease;
        z-index: 1001;
        writing-mode: vertical-rl;
        text-orientation: mixed;
    }}
    .floating-toggle:hover {{
        background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%);
        box-shadow: 0 12px 24px rgba(37, 99, 235, 0.4);
    }}
    .floating-toggle.open {{
        right: 400px;
        border-radius: 0 50px 50px 0;
    }}
    /* Home Overview Styles */
    .home-container {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }}
    .welcome-section {{
        text-align: center;
        margin: 0 0 10px 0;
    }}
    .app-logo {{
        font-size: 4rem;
        margin: 0 0 0 0;
    }}
    .app-title {{
        font-family: 'Cambria', serif;
        font-size: 6rem;
        font-weight: 700;
        color: #1F2937;
        margin: 0;
        line-height: 0.8;
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}
    .app-subtitle {{
        font-family: 'Cambria', serif;
        font-size: 1.8rem;
        color: #6B7280;
        margin: 0;
        line-height: 1;
    }}
    .quick-buttons {{
        display: flex;
        gap: 15px;
        justify-content: center;
        flex-wrap: wrap;
        margin-bottom: 40px;
    }}
    .quick-btn {{
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-family: 'Cambria', serif;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.2);
    }}
    .quick-btn:hover {{
        background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%);
        box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3);
        transform: translateY(-2px);
    }}
    .summary-cards {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin-bottom: 40px;
    }}
    .summary-card {{
        background: #FFC7CF;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1.5px solid #051B4A;
        text-align: center;
        transition: all 0.3s ease;
        height: 300px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }}
    .summary-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
    }}
    .summary-card-icon {{
        font-size: 2.5rem;
        margin-bottom: 12px;
        flex-shrink: 0;
    }}
    .summary-card-title {{
        font-family: 'Cambria', serif;
        font-size: 1.1rem;
        font-weight: bold;
        color: #232527;
        margin-bottom: 8px;
        flex-shrink: 0;
    }}
    .summary-card-value {{
        font-family: 'Cambria', serif;
        font-size: 2rem;
        font-weight: 700;
        color: #2563EB;
        margin-bottom: 8px;
        flex-shrink: 0;
    }}
    .summary-card-desc {{
        font-family: 'Cambria', serif;
        font-size: 0.9rem;
        font-weight: bold;
        color: #232527;
        flex-grow: 1;
        display: flex;
        align-items: flex-end;
    }}
    /* System Status Styles */
    .system-status {{
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        border: 1.5px solid #000000;
    }}
    .status-item {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1.5px solid #FFC7CF;
    }}
    .status-item:last-child {{
        border-bottom: none;
    }}
    .status-label {{
        font-family: 'Cambria', serif;
        font-size: 0.9rem;
        font-weight: bold;
        color: #232527;
    }}
    .status-value {{
        font-family: 'Cambria', serif;
        font-size: 0.9rem;
        font-weight: bold;
    }}
    .status-online {{
        color: #10B981;
    }}
    .status-offline {{
        color: #EF4444;
    }}
    .status-warning {{
        color: #F59E0B;
    }}
    /* Let sidebar navigation use default fonts - no overrides */
    [data-testid="stSidebarNav"] {{
        font-family: inherit !important;
    }}
    [data-testid="stSidebarNav"] * {{
        font-family: inherit !important;
    }}
    /* Make sidebar dividers bold */
    .stSidebar hr {{
        border: none !important;
        height: 2px !important;
        background: {colors['primary']} !important;
        margin: 15px 0 !important;
        border-radius: 1.5px !important;
    }}
    </style>
    <script>
    function fixBackButton() {{
        // Simple text replacement
        const elements = document.querySelectorAll('*');
        elements.forEach(element => {{
            if (element.textContent && element.textContent.includes('keyboard_double_arrow_right')) {{
                element.innerHTML = element.innerHTML.replace(/keyboard_double_arrow_right/g, '>>');
            }}
        }});
    }}
    // Run multiple times to catch dynamic content
    fixBackButton();
    setTimeout(fixBackButton, 500);
    setTimeout(fixBackButton, 1000);
    </script>
    """

def load_custom_css():
    """Load optimized CSS with light theme."""
    st.markdown(get_optimized_css(), unsafe_allow_html=True)
