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
        "text_secondary": "#000000",
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
    /* Import Inter & Cambria fonts and Material Icons */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Cambria:wght@400;700&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');

    /* Global Styles */
    .main {{
        background-color: {colors['bg_main']} !important;
        font-family: 'Cambria', Georgia, serif !important;
    }}

    /* Force theme colors on main containers */
    .stApp {{
        background-color: {colors['bg_main']} !important;
    }}

    div[data-testid="stAppViewContainer"] {{
        background-color: {colors['bg_main']} !important;
    }}

    /* Global typography system using Cambria as default & FORCE BOLD */
    body, p, div:not([class*="icon"]):not([class*="Icon"]):not([class*="material"]):not([class*="st-"]), span:not([class*="icon"]):not([class*="Icon"]):not([class*="material"]):not([class*="st-"]), label, input, textarea, select, option, button, h1, h2, h3, h4, h5, h6, a, li, td, th {{
        font-family: 'Cambria', Georgia, serif !important;
        font-weight: bold !important;
    }}

    /* Global Center Alignment for all contents of all pages (main content section only) & Top Padding for Safety */
    section:not([data-testid="stSidebar"]) .block-container {{
        text-align: center !important;
        padding-top: 4rem !important;
        margin-top: 0px !important;
    }}

    /* Align all texts to center on main pages, keeping layouts intact */
    section:not([data-testid="stSidebar"]) p,
    section:not([data-testid="stSidebar"]) span:not([class*="icon"]):not([class*="Icon"]):not([class*="material"]):not([class*="st-"]),
    section:not([data-testid="stSidebar"]) label,
    section:not([data-testid="stSidebar"]) div.stMarkdown,
    section:not([data-testid="stSidebar"]) div.stText,
    section:not([data-testid="stSidebar"]) h1,
    section:not([data-testid="stSidebar"]) h2,
    section:not([data-testid="stSidebar"]) h3,
    section:not([data-testid="stSidebar"]) h4,
    section:not([data-testid="stSidebar"]) h5,
    section:not([data-testid="stSidebar"]) h6 {{
        text-align: center !important;
    }}

    /* Center widgets/elements horizontally within their containers without breaking them */
    section:not([data-testid="stSidebar"]) div[data-testid="element-container"] {{
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
    }}

    /* Center rows of columns horizontally */
    section:not([data-testid="stSidebar"]) div[data-testid="stHorizontalBlock"] {{
        justify-content: center !important;
        align-items: center !important;
    }}

    /* Prevent buttons from wrapping text to multiple lines */
    .stButton button, button[data-testid^="stBaseButton"] {{
        white-space: nowrap !important;
    }}

    /* Headings and Titles - Bigger in size & bold & centered (only on main page, not sidebar) */
    section:not([data-testid="stSidebar"]) h1 {{
        font-size: 3.5rem !important;
        font-weight: bold !important;
        color: #051B4A !important;
        text-align: center !important;
        margin-bottom: 20px !important;
    }}

    section:not([data-testid="stSidebar"]) h2 {{
        font-size: 2.8rem !important;
        font-weight: bold !important;
        color: #051B4A !important;
        text-align: center !important;
        margin-bottom: 15px !important;
    }}

    section:not([data-testid="stSidebar"]) h3 {{
        font-size: 2.2rem !important;
        font-weight: bold !important;
        color: #051B4A !important;
        text-align: center !important;
    }}

    section:not([data-testid="stSidebar"]) h4,
    section:not([data-testid="stSidebar"]) h5,
    section:not([data-testid="stSidebar"]) h6 {{
        font-size: 1.6rem !important;
        font-weight: bold !important;
        color: #051B4A !important;
        text-align: center !important;
    }}

    /* Cambria reserved strictly for main brand titles */
    .app-title, .brand-title, .landing-brand, h1.app-title, #stratix-wordmark {{
        font-family: 'Cambria', Georgia, serif !important;
        font-weight: bold !important;
    }}

    /* Apply Cambria to all interactive elements */
    .stButton, .stButton > button, .stSelectbox, .stTextInput, .stTextArea {{
        font-family: 'Cambria', Georgia, serif !important;
        font-weight: bold !important;
    }}

    /* Do not override icon fonts and reset their weight so they don't break */
    .material-icons, [class*="material-icons"], [class*="Icon-"], [data-testid="collapsedSidebarCodegen"] *, [data-testid="stSidebarCollapseButton"] * {{
        font-family: 'Material Icons', sans-serif !important;
        font-weight: normal !important;
    }}

    /* Sidebar Styling and Typography */
    .stSidebar .stMarkdown, .stSidebar .stText, .stSidebar div {{
        font-family: 'Cambria', Georgia, serif !important;
    }}

    .stSidebar span:not([class*="icon"]):not([class*="Icon"]):not([class*="material"]) {{
        font-family: 'Cambria', Georgia, serif !important;
    }}

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
    .stButton button, button[data-testid^="stBaseButton"] {{
        background-color: {colors['primary']} !important;
        color: {colors['text_white']} !important;
        border: 2px solid {colors['border_dark']} !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        font-family: 'Cambria', serif !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }}
    .stButton button *, button[data-testid^="stBaseButton"] * {{
        color: {colors['text_white']} !important;
    }}
    .stButton button:hover, button[data-testid^="stBaseButton"]:hover {{
        background-color: {colors['primary_hover']} !important;
        color: {colors['primary']} !important;
        box-shadow: 0 4px 8px {colors['primary']}30 !important;
    }}
    .stButton button:hover *, button[data-testid^="stBaseButton"]:hover * {{
        color: {colors['primary']} !important;
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
        color: {colors['primary']};
        padding: 10px 5px;
        margin-bottom: 20px;
        text-align: center;
    }}
    .sidebar-header h2 {{
        font-family: 'Cambria', serif;
        font-size: 1.4rem;
        font-weight: bold;
        margin: 0;
        color: {colors['primary']};
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
        font-weight: 500 !important;
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
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }}
    /* Sidebar Buttons */
    .stSidebar .stButton button {{
        border: 2px solid #051B4A !important;
        border-radius: 8px !important;
        font-family: 'Cambria', serif !important;
        font-weight: 500 !important;
        padding: 10px 16px !important;
        height: auto !important;
        display: block !important;
        width: 100% !important;
        box-sizing: border-box !important;
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
        color: #051B4A !important;
        margin: 0;
        line-height: 0.8;
    }}
    .app-subtitle {{
        font-family: 'Cambria', serif;
        font-size: 1.8rem;
        color: #051B4A !important;
        margin: 0;
        line-height: 1;
        font-weight: bold !important;
        font-style: italic !important;
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
        height: auto;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 20px;
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
        align-items: flex-start;
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

    /* Custom CSS to replace sidebar collapse/expand buttons with << and >> */
    button[data-testid="stSidebarCollapseButton"] *,
    [data-testid="collapsedSidebarCodegen"] button * {{
        font-size: 0 !important;
        color: transparent !important;
        display: none !important;
    }}

    button[data-testid="stSidebarCollapseButton"]::after {{
        content: "<<" !important;
        font-family: 'Cambria', Georgia, serif !important;
        font-size: 1.2rem !important;
        color: #051B4A !important;
        visibility: visible !important;
        display: inline-block !important;
    }}

    [data-testid="collapsedSidebarCodegen"] button::after {{
        content: ">>" !important;
        font-family: 'Cambria', Georgia, serif !important;
        font-size: 1.2rem !important;
        color: #051B4A !important;
        visibility: visible !important;
        display: inline-block !important;
    }}

    section:not([data-testid="stSidebar"]) h3.left-aligned-title,
    h3.left-aligned-title {{
        text-align: left !important;
        font-family: 'Cambria', Georgia, serif !important;
        font-size: 1.6rem !important;
        font-weight: bold !important;
        color: #051B4A !important;
        margin-top: 30px !important;
        margin-bottom: 15px !important;
        width: 100% !important;
        display: block !important;
    }}

    section:not([data-testid="stSidebar"]) div[data-testid="element-container"]:has(.left-aligned-title) {{
        display: flex !important;
        justify-content: flex-start !important;
        width: 100% !important;
    }}

    /* Explicitly Center the Welcome Logo and Brand Section */
    .welcome-section, .app-logo, .welcome-section * {{
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        margin: 0 auto !important;
    }}
    .welcome-section {{
        gap: 0px !important;
    }}
    .app-title {{
        margin-top: 5px !important;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        line-height: 0.9 !important;
    }}
    .app-subtitle {{
        margin-top: 0px !important;
        margin-bottom: 10px !important;
        padding-top: 0px !important;
        line-height: 1.0 !important;
    }}
    .welcome-section img {{
        display: block !important;
        margin: 0 auto !important;
    }}

    /* Hide Streamlit's keyboard shortcut/tooltip overlays globally */
    div[data-baseweb="tooltip"],
    div[role="tooltip"],
    div[class*="tooltip"] {{
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0px !important;
        width: 0px !important;
        overflow: hidden !important;
    }}
    </style>
    """

def load_custom_css():
    """Load optimized CSS with light theme."""
    st.markdown(get_optimized_css(), unsafe_allow_html=True)
