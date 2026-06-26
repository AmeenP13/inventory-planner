import streamlit as st
import os

# Set page configuration to wide layout and set title/icon
st.set_page_config(
    page_title="StockMind Replenishment AI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS styling
def load_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"CSS file {file_name} not found.")

load_css("style.css")

# Helper function to get current page from URL query parameters
def get_current_page():
    try:
        # st.query_params is a dict-like object in Streamlit 1.30+
        page_val = st.query_params.get("page", "Overview")
        if isinstance(page_val, list):
            return page_val[0]
        return page_val
    except Exception:
        # Fallback to session state if query_params fails or is unsupported
        if "page" not in st.session_state:
            st.session_state.page = "Overview"
        return st.session_state.page

# Set session state page based on URL query parameter
st.session_state.page = get_current_page()

# Sidebar Header - App Logo & Title
sidebar_header_html = (
    '<div class="sidebar-header">'
    '<div class="logo-box">'
    '<span class="logo-icon">📦</span>'
    '</div>'
    '<div class="title-container">'
    '<div class="main-title">StockMind</div>'
    '<div class="sub-title">REPLENISHMENT AI</div>'
    '</div>'
    '</div>'
)
st.sidebar.markdown(sidebar_header_html, unsafe_allow_html=True)

# Custom HTML Sidebar Navigation Menu
pages = [
    {"name": "Overview", "icon": "🏠", "badge": None},
    {"name": "Inventory", "icon": "📦", "badge": "5"},
    {"name": "Demand", "icon": "📊", "badge": None},
    {"name": "Suppliers", "icon": "🚚", "badge": None},
    {"name": "AI Agent", "icon": "⚡", "badge": None},
]

# Build navigation HTML
nav_html = '<div class="sidebar-menu">'
for p in pages:
    # We map 'AI Agent' page to URL parameter 'Agent' for simplicity
    url_name = "Agent" if p["name"] == "AI Agent" else p["name"]
    is_active = st.session_state.page == url_name
    active_class = "active" if is_active else ""
    badge_html = f'<span class="nav-badge">{p["badge"]}</span>' if p["badge"] else ""
    
    nav_html += (
        f'<a href="?page={url_name}" class="nav-item {active_class}" target="_self">'
        f'<span class="nav-icon">{p["icon"]}</span>'
        f'<span class="nav-label">{p["name"]}</span>'
        f'{badge_html}'
        '</a>'
    )
nav_html += "</div>"

# Render navigation menu
st.sidebar.markdown(nav_html, unsafe_allow_html=True)

# Trigger AI Replenishment Button
st.sidebar.markdown('<div class="trigger-btn-container">', unsafe_allow_html=True)
if st.sidebar.button("⚡ Trigger AI Replenishment", key="trigger_replenish"):
    st.toast("⚡ AI Replenishment process triggered!", icon="🤖")
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Sidebar Footer
sidebar_footer_html = (
    '<div class="sidebar-footer">'
    '<div class="warehouse-info">'
    '<div class="wh-title">Warehouse #3</div>'
    '<div class="wh-sub">STO-WH03-PDX</div>'
    '</div>'
    '<div class="settings-icon">⚙️</div>'
    '</div>'
)
st.sidebar.markdown(sidebar_footer_html, unsafe_allow_html=True)

# Render Injected Styling to handle active navigation link border & background
# Just in case, to ensure color consistency
st.markdown(
    f"""
    <style>
    /* Injected active state styling for side menu item */
    .nav-item.active {{
        background-color: #C2E2F5 !important;
        color: #0E4B75 !important;
        font-weight: 600 !important;
        border-left: 4px solid #00A8CC !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Main Page Layout ---

# Page routing name mapping back
display_page_name = "AI Agent" if st.session_state.page == "Agent" else st.session_state.page

# Header container
col_title, col_actions = st.columns([3, 2])

with col_title:
    if st.session_state.page == "Overview":
        st.markdown(
            """
            <div class="header-left">
                <div class="header-breadcrumbs">Overview &gt; Warehouse PDX-03</div>
                <div class="header-title">Warehouse Dashboard Overview</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif st.session_state.page == "Inventory":
        st.markdown(
            """
            <div class="header-left">
                <div class="header-breadcrumbs">Inventory &gt; Real-time Stock</div>
                <div class="header-title">Inventory Overview & Management</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif st.session_state.page == "Demand":
        st.markdown(
            """
            <div class="header-left">
                <div class="header-breadcrumbs">Demand &gt; Sales Velocity</div>
                <div class="header-title">Product Demand Trends</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif st.session_state.page == "Suppliers":
        st.markdown(
            """
            <div class="header-left">
                <div class="header-breadcrumbs">Suppliers &gt; Performance Matrix</div>
                <div class="header-title">Supplier Management & Metrics</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif st.session_state.page == "Agent":
        st.markdown(
            """
            <div class="header-left">
                <div class="header-breadcrumbs">AI Agent &gt; Decisions</div>
                <div class="header-title">Autonomous Replenishment Proposals</div>
            </div>
            """,
            unsafe_allow_html=True
        )

with col_actions:
    # A search input and actions aligned horizontally
    sub_col1, sub_col2, sub_col3 = st.columns([4, 1, 1])
    with sub_col1:
        st.text_input("Search", placeholder="Search products, SKUs, suppliers...", label_visibility="collapsed")
    with sub_col2:
        st.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: center; height: 38px; font-size: 20px; cursor: pointer; background: white; border-radius: 8px; border: 1px solid #E2E8F0; width: 38px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                🔔
            </div>
            """,
            unsafe_allow_html=True
        )
    with sub_col3:
        st.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: center; height: 38px; font-size: 20px; cursor: pointer; background: white; border-radius: 8px; border: 1px solid #E2E8F0; width: 38px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                👤
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("---")

# Main Content Routing Display
if st.session_state.page == "Overview":
    st.markdown(
        """
        <div style="background-color: white; padding: 40px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); text-align: center;">
            <h3 style="color: #0F172A; margin-bottom: 10px;">Overview Page</h3>
            <p style="color: #64748B;">Day 1: Shell initialized successfully. Static dashboard metrics, charts, and warehouse KPIs will be implemented here on Day 2.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
elif st.session_state.page == "Inventory":
    st.markdown(
        """
        <div style="background-color: white; padding: 40px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); text-align: center;">
            <h3 style="color: #0F172A; margin-bottom: 10px;">Inventory Page</h3>
            <p style="color: #64748B;">Day 1: Shell initialized successfully. The interactive inventory table with days-left progress bars, category filters, and status badges will be implemented here on Day 2.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
elif st.session_state.page == "Demand":
    st.markdown(
        """
        <div style="background-color: white; padding: 40px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); text-align: center;">
            <h3 style="color: #0F172A; margin-bottom: 10px;">Demand Trends Page</h3>
            <p style="color: #64748B;">Day 1: Shell initialized successfully. High-demand product highlights, category-wise demand velocity charts, and ROI calculations will be implemented here on Day 2 & 3.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
elif st.session_state.page == "Suppliers":
    st.markdown(
        """
        <div style="background-color: white; padding: 40px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); text-align: center;">
            <h3 style="color: #0F172A; margin-bottom: 10px;">Suppliers Page</h3>
            <p style="color: #64748B;">Day 1: Shell initialized successfully. Supplier performance matrix charts and reliability metrics will be implemented here on Day 2.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
elif st.session_state.page == "Agent":
    st.markdown(
        """
        <div style="background-color: white; padding: 40px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); text-align: center;">
            <h3 style="color: #0F172A; margin-bottom: 10px;">Autonomous AI Agent Replenishment Proposal</h3>
            <p style="color: #64748B;">Day 1: Shell initialized successfully. The AI Agent's final policy-checked recommendation cards and order approval actions will be implemented here on Day 4.</p>
        </div>
        """,
        unsafe_allow_html=True
    )
