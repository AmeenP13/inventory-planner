import requests
import streamlit as st
import streamlit.components.v1 as components
import json
import os
import pandas as pd
import altair as alt
import time

# 1. Set Page Configuration
st.set_page_config(
    page_title="StockMind - Replenishment AI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. API & Mock Data Loader Helper
MOCK_DIR = os.path.join(os.path.dirname(__file__), "mock")
API_BASE_URL = "http://127.0.0.1:8000"


def load_mock_json(filename):
    path = os.path.join(MOCK_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    st.error(f"Mock file not found: {filename}")
    return {}


def get_api_data(endpoint, fallback_filename):
    try:
        res = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        pass
    return load_mock_json(fallback_filename)


# Load datasets using reload helper and session state caching
def reload_all_data():
    st.session_state.overview_data = get_api_data("/api/overview", "overview_data.json")
    inventory_data = get_api_data("/api/inventory_report", "inventory_data.json")
    st.session_state.inventory_db = pd.DataFrame(inventory_data)
    st.session_state.demand_data = get_api_data("/api/demand_report", "demand_data.json")
    st.session_state.suppliers_data = get_api_data("/api/suppliers_report", "suppliers_data.json")

if "overview_data" not in st.session_state:
    st.session_state.overview_data = get_api_data("/api/overview", "overview_data.json")

if "inventory_db" not in st.session_state:
    inventory_data = get_api_data("/api/inventory_report", "inventory_data.json")
    st.session_state.inventory_db = pd.DataFrame(inventory_data)

if "demand_data" not in st.session_state:
    st.session_state.demand_data = get_api_data("/api/demand_report", "demand_data.json")

if "suppliers_data" not in st.session_state:
    st.session_state.suppliers_data = get_api_data("/api/suppliers_report", "suppliers_data.json")

overview_data = st.session_state.overview_data
inventory_data = st.session_state.inventory_db.to_dict('records') if hasattr(st.session_state.inventory_db, "to_dict") else list(st.session_state.inventory_db)
demand_data = st.session_state.demand_data
suppliers_data = st.session_state.suppliers_data

if "agent_proposal" not in st.session_state:
    st.session_state.agent_proposal = get_api_data(
        "/api/proposal", "agent_proposal.json")

if "proposal_db" not in st.session_state and st.session_state.agent_proposal:
    st.session_state.proposal_db = st.session_state.agent_proposal["recommendations"]

# Notify user of low stock alerts on initial load
if "notified_low_stock" not in st.session_state:
    alerts = overview_data.get("alerts", [])
    if alerts:
        critical_count = sum(
            1 for a in alerts if a.get("status") == "CRITICAL")
        low_count = sum(1 for a in alerts if a.get("status") == "LOW STOCK")
        msg = f"Alert: {critical_count} critical out-of-stock and {low_count} low-stock items detected!"
        st.toast(msg, icon="🚨")
    st.session_state.notified_low_stock = True


# Dynamic badge: count items needing attention from live inventory
if "inventory_db" in st.session_state:
    _badge_df = st.session_state.inventory_db
    inventory_badge_count = int(len(_badge_df[_badge_df["status"].isin(["CRITICAL", "LOW STOCK", "OUT OF STOCK"])]))
else:
    inventory_badge_count = len([x for x in inventory_data if x.get("status") in ["CRITICAL", "LOW STOCK", "OUT OF STOCK"]]) if inventory_data else 0

# 3. HTML & CSS Render Helpers
def render_progress_bar(days_left):
    max_days = 14.0
    pct = min(100.0, (days_left / max_days) * 100.0) if days_left > 0 else 0.0

    # Determine color matching mockup
    if days_left == 0:
        bar_color = "#E2E8F0"  # Gray empty
        text_color = "#E63946"  # Red text for 0d
    elif days_left <= 2.0:
        bar_color = "#E63946"  # Red
        text_color = "#E63946"
    elif days_left <= 5.0:
        bar_color = "#F39C12"  # Yellow/Orange
        text_color = "#F39C12"
    else:
        bar_color = "#2ECC71"  # Green
        text_color = "#2ECC71"

    return f"""
    <div style="display: flex; align-items: center; gap: 8px;">
        <div style="background-color: #E2E8F0; width: 60px; height: 6px; border-radius: 3px; overflow: hidden; position: relative;">
            <div style="background-color: {bar_color}; width: {pct}%; height: 100%;"></div>
        </div>
        <span style="color: {text_color}; font-weight: 600; font-size: 13px;">{days_left}d</span>
    </div>
    """


def render_status_badge(status):
    status = status.upper()
    if status in ["CRITICAL", "URGENT ORDER"]:
        bg = "#FEE2E2"
        color = "#EF4444"
    elif status == "LOW STOCK":
        bg = "#FEF3C7"
        color = "#D97706"
    elif status == "HEALTHY":
        bg = "#D1FAE5"
        color = "#10B981"
    elif status == "OUT OF STOCK":
        bg = "#F3F4F6"
        color = "#EF4444"  # Red outline/text for out of stock
    else:
        bg = "#E0F2FE"
        color = "#0369A1"

    return f"""
    <span style="background-color: {bg}; color: {color}; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; display: inline-block; text-transform: uppercase; border: 1px solid {color}20;">
        {status}
    </span>
    """


def render_kpi_card(
        title,
        value,
        change,
        detail="",
        icon="📊",
        card_type="default"):
    if card_type == "yellow":
        bg_color = "#FFFBEB"
        border_color = "#FEF3C7"
        icon_bg = "#D97706"
    elif card_type == "red":
        bg_color = "#FEF2F2"
        border_color = "#FEE2E2"
        icon_bg = "#EF4444"
    elif card_type == "green":
        bg_color = "#ECFDF5"
        border_color = "#D1FAE5"
        icon_bg = "#10B981"
    elif card_type == "purple":
        bg_color = "#F5F3FF"
        border_color = "#EEDEFE"
        icon_bg = "#8B5CF6"
    else:
        bg_color = "#FFFFFF"
        border_color = "#E4EDF5"
        icon_bg = "#00A8C6"

    return f"""
    <div style="background-color: {bg_color}; border: 1px solid {border_color}; padding: 18px; border-radius: 12px; height: 100%; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 2px 4px rgba(28, 61, 90, 0.01);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <span style="font-size: 13px; font-weight: 600; color: #5B7A9C;">{title}</span>
            <span style="background-color: {icon_bg}1A; color: {icon_bg}; width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 14px;">{icon}</span>
        </div>
        <div>
            <div style="font-size: 26px; font-weight: 700; color: #1C3D5A; line-height: 1.1;">{value}</div>
            <div style="font-size: 11px; font-weight: 600; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                <span style="color: {"#EF4444" if "-" in change or "down" in change or "critical" in change or "Out of Stock" in title else "#10B981"};">{change}</span>
                <span style="color: #8CA0B8;">{detail}</span>
            </div>
        </div>
    </div>
    """


def render_highlight_card(product_name, sku, daily_avg, trend, days_left):
    bg_color = "#FFF5F5"
    border_color = "#FEB2B2"
    badge_color = "#E53E3E"

    if days_left <= 3.0:
        days_style = "color: #E53E3E; font-weight: 700;"
    elif days_left <= 7.0:
        days_style = "color: #DD6B20; font-weight: 700;"
    else:
        days_style = "color: #38A169; font-weight: 700;"

    return f"""
    <div style="background-color: {bg_color}; border: 1px solid {border_color}; padding: 15px; border-radius: 10px; display: flex; flex-direction: column; justify-content: space-between; height: 100%; box-shadow: 0 2px 5px rgba(229, 62, 62, 0.04);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <span style="background-color: #FED7D7; color: {badge_color}; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; border: 1px solid {badge_color}20;">🔥 High Demand</span>
            <span style="font-size: 11px; font-family: monospace; color: #718096; font-weight: 600;">{sku}</span>
        </div>
        <div style="font-size: 14px; font-weight: 700; color: #1C3D5A; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{product_name}">{product_name}</div>
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed #FEB2B2; padding-top: 8px; margin-top: 4px; font-size: 12px;">
            <div>
                <span style="color: #718096; display: block; font-size: 9px; text-transform: uppercase; font-weight: 600;">Daily Velocity</span>
                <span style="font-weight: 700; color: #E53E3E; font-size: 12px;">{daily_avg} units/day</span>
            </div>
            <div style="text-align: right;">
                <span style="color: #718096; display: block; font-size: 9px; text-transform: uppercase; font-weight: 600;">Days Remaining</span>
                <span style="{days_style}">{days_left}d left</span>
            </div>
        </div>
    </div>
    """


TABLE_BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Plus Jakarta Sans', sans-serif; background: transparent; }
"""


def render_table(df_data, is_snapshot=False):
    rows_html = ""
    for idx, row in df_data.iterrows():
        sku = row['sku']
        product = row['product']
        stock = row['stock']
        days_left = row['days_left']
        supplier = row['supplier']
        status = row['status']

        progress = render_progress_bar(days_left)
        badge = render_status_badge(status)
        stock_color = "#EF4444" if stock == 0 else "#1C3D5A"

        action_col = "" if is_snapshot else """
        <td style="padding: 14px 16px; text-align: center; color: #5B7A9C; font-size: 16px; cursor: pointer;">⋮</td>
        """

        rows_html += f"""
        <tr style="border-bottom: 1px solid #E4EDF5; color: #1C3D5A;">
            <td style="padding: 14px 16px; font-weight: 500; font-family: monospace; font-size:13px;">{sku}</td>
            <td style="padding: 14px 16px; font-weight: 600; color: #1C3D5A;">{product}</td>
            <td style="padding: 14px 16px; font-weight: 700; color: {stock_color};">{stock}</td>
            <td style="padding: 14px 16px;">{progress}</td>
            <td style="padding: 14px 16px; color: #4A607A;">{supplier}</td>
            <td style="padding: 14px 16px;">{badge}</td>
            {action_col}
        </tr>
        """

    extra_th = "" if is_snapshot else '<th style="padding: 14px 16px; text-align: center;">Actions</th>'
    html = f"""<!DOCTYPE html><html><head><style>
    {TABLE_BASE_CSS}
    table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
    thead tr {{ background-color: #F8FAFC; color: #5B7A9C; border-bottom: 2px solid #E4EDF5; }}
    th {{ padding: 14px 16px; font-weight: 600; }}
    tbody tr:hover {{ background-color: #F8FAFC; }}
    </style></head><body>
    <div style="border-radius: 12px; border: 1px solid #E4EDF5; overflow: hidden; box-shadow: 0 2px 4px rgba(28,61,90,0.03);">
    <table>
        <thead>
            <tr>
                <th>SKU</th><th>Product</th><th>Stock</th>
                <th>Days Left</th><th>Supplier</th><th>Status</th>
                {extra_th}
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    </div></body></html>"""
    return html


# 4. Premium Injected CSS Stylesheet
st.markdown("""
<style>
    /* Fonts and Overall Aesthetics */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #F3F7FA !important;
        color: #1C3D5A;
    }

    /* Style the Sidebar Container */
    [data-testid="stSidebar"] {
        background-color: #EBF3FC !important;
        border-right: 1px solid #D5E3F0;
        padding-top: 10px;
    }

    /* Remove default Streamlit sidebar paddings */
    [data-testid="stSidebarUserContent"] {
        padding-top: 20px !important;
        padding-bottom: 20px !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100vh;
    }

    /* Navigation Menu Styles */
    .nav-container {
        margin-top: 15px;
        margin-bottom: 15px;
    }

    .nav-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        border-radius: 8px;
        color: #4A607A;
        text-decoration: none;
        font-weight: 500;
        font-size: 15px;
        margin-bottom: 6px;
        transition: all 0.2s ease-in-out;
    }

    .nav-item:hover {
        background-color: #DCE9F6;
        color: #1C3D5A;
    }

    .nav-item.active {
        background-color: #BFE3F9;
        color: #1C3D5A;
        font-weight: 600;
        border-left: 4px solid #00A8C6;
        border-radius: 0 8px 8px 0;
    }

    .nav-link {
        display: flex;
        align-items: center;
        gap: 12px;
        text-decoration: none;
        color: inherit;
        width: 100%;
    }

    .nav-icon {
        font-size: 18px;
    }

    /* Badge styling */
    .badge {
        background-color: #E63946;
        color: white;
        border-radius: 12px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 700;
    }

    /* Sidebar Trigger Action Button */
    .trigger-btn-container {
        margin-top: 20px;
        padding: 0 5px;
    }

    .trigger-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        background-color: #00A8C6;
        color: white !important;
        border: none;
        padding: 14px 20px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 15px;
        text-decoration: none;
        width: 100%;
        box-shadow: 0 4px 6px rgba(0, 168, 198, 0.15);
        transition: all 0.2s ease;
        text-align: center;
    }

    .trigger-btn:hover {
        background-color: #008fa8;
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(0, 168, 198, 0.25);
    }

    /* Sidebar Footer */
    .sidebar-footer {
        border-top: 1px solid #D5E3F0;
        padding-top: 15px;
        margin-top: auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .warehouse-info {
        font-size: 12px;
        color: #5B7A9C;
    }

    .warehouse-title {
        font-weight: 700;
        color: #1C3D5A;
        margin-bottom: 2px;
    }

    .settings-icon {
        color: #5B7A9C;
        font-size: 18px;
        cursor: pointer;
        transition: color 0.2s;
    }

    .settings-icon:hover {
        color: #1C3D5A;
    }

    /* Header CSS Styling */
    .header-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #FFFFFF;
        padding: 15px 25px;
        border-radius: 12px;
        border: 1px solid #E4EDF5;
        margin-bottom: 25px;
        box-shadow: 0 2px 4px rgba(28, 61, 90, 0.02);
    }

    .header-left {
        display: flex;
        flex-direction: column;
    }

    .header-title {
        font-weight: 700;
        font-size: 24px;
        color: #1C3D5A;
        margin: 0;
    }

    .header-subtitle {
        font-size: 13px;
        color: #5B7A9C;
        margin-top: 2px;
    }

    .header-right {
        display: flex;
        align-items: center;
        gap: 15px;
    }

    .search-input-mock {
        background-color: #F3F7FA;
        border: 1px solid #E4EDF5;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 14px;
        color: #5B7A9C;
        width: 250px;
        outline: none;
    }

    .bell-icon-container {
        position: relative;
        background-color: #F3F7FA;
        border: 1px solid #E4EDF5;
        border-radius: 8px;
        width: 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: background-color 0.2s;
    }

    .bell-badge {
        position: absolute;
        top: 8px;
        right: 8px;
        width: 8px;
        height: 8px;
        background-color: #E63946;
        border-radius: 50%;
    }

    .export-btn {
        background-color: #00A8C6;
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 9px 16px;
        font-size: 14px;
        font-weight: 600;
        text-decoration: none;
        transition: background-color 0.2s;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .export-btn:hover {
        background-color: #008fa8;
    }

    /* Circular Loading Spinner & Steps */
    .spinner-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 40px;
        background-color: #FFFFFF;
        border: 1px solid #E4EDF5;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(28, 61, 90, 0.05);
        max-width: 600px;
        margin: 60px auto;
    }

    .spinner {
        width: 50px;
        height: 50px;
        border: 4px solid #EBF3FC;
        border-top: 4px solid #00A8C6;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 25px;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .loading-step {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
        font-size: 13.5px;
        color: #5B7A9C;
        width: 100%;
        max-width: 480px;
        padding: 10px 18px;
        border-radius: 8px;
        background-color: #F8FAFC;
        border: 1px solid #E4EDF5;
        transition: all 0.3s ease;
    }

    .loading-step.active {
        color: #1C3D5A;
        font-weight: 600;
        border-color: #BFE3F9;
        background-color: #EBF3FC;
        box-shadow: 0 2px 4px rgba(0, 168, 198, 0.04);
    }

    .loading-step.done {
        color: #10B981;
        font-weight: 500;
        border-color: #D1FAE5;
        background-color: #F0FDF4;
    }

    .loading-step.pending {
        opacity: 0.65;
    }

    /* Layout Spacing & Spacing Polish */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }

    /* Hide Streamlit components */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# 5. Sidebar Brand & Navigation
with st.sidebar:
    # Logo Header
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 25px; padding: 5px 5px;">
        <div style="background-color: #00A8C6; padding: 10px; border-radius: 10px; color: white; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold; width: 42px; height: 42px; box-shadow: 0 4px 6px rgba(0,168,198,0.1);">
            🤖
        </div>
        <div>
            <div style="font-weight: 700; color: #1C3D5A; font-size: 18px; line-height: 1.2;">StockMind</div>
            <div style="font-size: 10px; color: #5B7A9C; letter-spacing: 1px; font-weight: 600;">REPLENISHMENT AI</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation Links (Using query parameters for route management)
    params = st.query_params
    selected_page = params.get("page", "Overview")

    # Set up navigation links with custom design and badge on Inventory
    st.markdown(f"""
    <div class="nav-container">
        <a href="?page=Overview" target="_self" class="nav-item {"active" if selected_page == "Overview" else ""}">
            <div class="nav-link">
                <span class="nav-icon">🏠</span>
                <span>Overview</span>
            </div>
        </a>
        <a href="?page=Inventory" target="_self" class="nav-item {"active" if selected_page == "Inventory" else ""}">
            <div class="nav-link">
                <span class="nav-icon">📦</span>
                <span>Inventory</span>
            </div>
            <span class="badge">{inventory_badge_count}</span>
        </a>
        <a href="?page=Demand" target="_self" class="nav-item {"active" if selected_page == "Demand" else ""}">
            <div class="nav-link">
                <span class="nav-icon">📊</span>
                <span>Demand</span>
            </div>
        </a>
        <a href="?page=Suppliers" target="_self" class="nav-item {"active" if selected_page == "Suppliers" else ""}">
            <div class="nav-link">
                <span class="nav-icon">🚚</span>
                <span>Suppliers</span>
            </div>
        </a>
        <a href="?page=AI_Agent" target="_self" class="nav-item {"active" if selected_page == "AI_Agent" else ""}">
            <div class="nav-link">
                <span class="nav-icon">⚡</span>
                <span>AI Agent</span>
            </div>
        </a>
    </div>
    """, unsafe_allow_html=True)

    # Action Button: Trigger AI Replenishment
    st.markdown("""
    <div class="trigger-btn-container">
        <a href="?page=AI_Agent&run=true" target="_self" class="trigger-btn">
            <span>⚡</span> Trigger AI Replenishment
        </a>
    </div>
    """, unsafe_allow_html=True)

    # Padding spacing
    st.write("")

    # Sticky Sidebar Footer (Warehouse Select)
    st.markdown("""
    <div class="sidebar-footer">
        <div class="warehouse-info">
            <div class="warehouse-title">Warehouse #3</div>
            <div>STO-WH03-PDX</div>
        </div>
        <div class="settings-icon">⚙️</div>
    </div>
    """, unsafe_allow_html=True)

# 6. Main Page Header Bar
header_title_map = {
    "Overview": "Overview",
    "Inventory": "Inventory",
    "Demand": "Demand",
    "Suppliers": "Suppliers",
    "AI_Agent": "AI Replenishment Proposal"
}

header_subtitle_map = {
    "Overview": "Warehouse PDX-03 key indicators",
    "Inventory": "Real-time stock overview and management",
    "Demand": "Sales forecasting and consumption analysis",
    "Suppliers": "Active vendors and performance metrics",
    "AI_Agent": "AI-generated recommendations and compliance logs"
}

current_title = header_title_map.get(selected_page, "Overview")
current_subtitle = header_subtitle_map.get(selected_page, "")

# Render Header HTML
st.markdown(f"""
<div class="header-bar">
    <div class="header-left">
        <div class="header-title">{current_title}</div>
        <div class="header-subtitle">{current_subtitle}</div>
    </div>
    <div class="header-right">
        <input type="text" class="search-input-mock" placeholder="Search products, SKUs, suppliers..." />
        <div class="bell-icon-container">
            <span>🔔</span>
            <div class="bell-badge"></div>
        </div>
        <a href="#" class="export-btn">
            <span>📥</span> Export Report
        </a>
    </div>
</div>
""", unsafe_allow_html=True)

# 7. Render Pages
# ----------------------------------------------------
# PAGE A: OVERVIEW
# ----------------------------------------------------
if selected_page == "Overview":
    # Load Overview Data
    summary = overview_data.get("summary", {})

    # KPI Row
    col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)

    with col_kpi1:
        st.markdown(
            render_kpi_card(
                "Total SKUs",
                summary["total_skus"]["value"],
                summary["total_skus"]["change"],
                "Across 9 categories",
                "📦",
                "default"),
            unsafe_allow_html=True)
    with col_kpi2:
        st.markdown(
            render_kpi_card(
                "Needs Action",
                summary["needs_action"]["value"],
                summary["needs_action"]["change"],
                summary["needs_action"]["detail"],
                "⚠️",
                "yellow"),
            unsafe_allow_html=True)
    with col_kpi3:
        st.markdown(
            render_kpi_card(
                "Avg Daily Velocity",
                summary["avg_velocity"]["value"],
                summary["avg_velocity"]["change"],
                summary["avg_velocity"]["detail"],
                "📈",
                "green"),
            unsafe_allow_html=True)
    with col_kpi4:
        st.markdown(
            render_kpi_card(
                "Avg SKUs",
                summary["avg_skus"]["value"],
                summary["avg_skus"]["change"],
                summary["avg_skus"]["detail"],
                "⏱️",
                "default"),
            unsafe_allow_html=True)
    with col_kpi5:
        st.markdown(
            render_kpi_card(
                "Critical Alerts",
                summary["critical_alerts"]["value"],
                summary["critical_alerts"]["change"],
                "Urgent attention",
                "🚨",
                "red"),
            unsafe_allow_html=True)

    # Demanded Products Highlight Section
    st.markdown("""
    <div style="font-weight: 700; color: #1C3D5A; font-size: 16px; margin-top: 15px; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;">
        <span>🔥</span> Demanded Products Highlight
    </div>
    """, unsafe_allow_html=True)

    col_high1, col_high2, col_high3 = st.columns(3)
    top_velocity_items = demand_data.get("top_velocity_skus", [])[:3]
    for idx, item in enumerate(top_velocity_items):
        card_html = render_highlight_card(
            item["product"],
            item["sku"],
            item["daily_avg"],
            item["trend"],
            item["days_remaining"]
        )
        if idx == 0:
            col_high1.markdown(card_html, unsafe_allow_html=True)
        elif idx == 1:
            col_high2.markdown(card_html, unsafe_allow_html=True)
        elif idx == 2:
            col_high3.markdown(card_html, unsafe_allow_html=True)

    st.write("")

    # Main content / Split
    col_main, col_alerts = st.columns([3.2, 1.2])

    with col_main:
        # Chart: Demand Trend - Last 13 Days
        st.markdown("""
        <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <div style="font-weight: 700; color: #1C3D5A; font-size: 16px; margin-bottom: 2px;">Demand Trend - Last 13 Days</div>
            <div style="font-size: 12px; color: #5B7A9C; margin-bottom: 15px;">Units sold by category</div>
        </div>
        """, unsafe_allow_html=True)

        # Draw Altair Line & Area chart
        df_trend = pd.DataFrame(overview_data.get("demand_trend", []))
        df_melt = df_trend.melt(
            id_vars=["date"],
            var_name="Category",
            value_name="Units Sold")

        base = alt.Chart(df_melt).encode(
            x=alt.X(
                'date:N', sort=None, title=None), y=alt.Y(
                'Units Sold:Q', title=None), color=alt.Color(
                'Category:N', scale=alt.Scale(
                    domain=[
                        'Electronics', 'Beverages', 'Health', 'Fitness'], range=[
                            '#00B4D8', '#4CAF50', '#FF9800', '#9C27B0']), legend=None))
        lines = base.mark_line(interpolate='monotone', strokeWidth=3.5)
        areas = base.mark_area(interpolate='monotone', opacity=0.08)
        chart = (areas + lines).properties(height=260).configure_axis(
            gridOpacity=0.2,
            gridDash=[2, 2],
            labelColor='#8CA0B8',
            tickColor='transparent'
        ).configure_view(
            strokeWidth=0
        )
        st.altair_chart(chart, use_container_width=True)

        # Legend custom rendering in HTML
        st.markdown("""
        <div style="display: flex; justify-content: center; gap: 20px; font-size: 13px; font-weight: 600; margin-top: -10px; margin-bottom: 25px;">
            <span style="color: #00B4D8; display: flex; align-items: center; gap: 6px;">● Electronics</span>
            <span style="color: #4CAF50; display: flex; align-items: center; gap: 6px;">● Beverages</span>
            <span style="color: #FF9800; display: flex; align-items: center; gap: 6px;">● Health</span>
            <span style="color: #9C27B0; display: flex; align-items: center; gap: 6px;">● Fitness</span>
        </div>
        """, unsafe_allow_html=True)

        # Inventory Snapshot Table
        st.markdown("""
        <div style="font-weight: 700; color: #1C3D5A; font-size: 16px; margin-bottom: 12px; margin-top: 10px;">Inventory Snapshot</div>
        """, unsafe_allow_html=True)

        df_snapshot = pd.DataFrame(overview_data.get("snapshot_inventory", []))
        n_rows_snap = len(df_snapshot)
        components.html(
            render_table(
                df_snapshot,
                is_snapshot=True),
            height=68 +
            n_rows_snap *
            58,
            scrolling=False)

    with col_alerts:
        # Critical Alerts Panel
        st.markdown("""
        <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 20px; min-height: 520px; display: flex; flex-direction: column;">
            <div style="font-weight: 700; color: #1C3D5A; font-size: 17px; margin-bottom: 15px;">Critical Alerts</div>
        """, unsafe_allow_html=True)

        # Alert List rendering
        for item in overview_data.get("alerts", []):
            is_critical = item["status"] == "CRITICAL"
            badge_color = "#E63946" if is_critical else (
                "#F59E0B" if item["status"] == "LOW STOCK" else "#94A3B8")
            badge_bg = "#FEE2E2" if is_critical else (
                "#FEF3C7" if item["status"] == "LOW STOCK" else "#F3F4F6")

            # Draw progress bar for alerts
            progress_pct = min(100.0, (item["days_left"] / 14.0) * 100.0)

            # Render Alert Card first
            st.markdown(f"""
            <div style="background-color: #F8FAFC; border: 1px solid #E4EDF5; border-radius: 8px; padding: 12px; margin-bottom: 8px; display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 700; font-size: 13px; color: #1C3D5A; max-width: 140px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{item["product"]}">{item["product"]}</span>
                    <span style="background-color: {badge_bg}; color: {badge_color}; font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 4px; border: 1px solid {badge_color}30;">{item["status"]}</span>
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px; color: #8CA0B8;">
                    <span>{item["sku"]}</span>
                    <span style="color: {badge_color}; font-weight: 700;">{item["days_left"]}d remaining</span>
                </div>
                <div style="background-color: #E2E8F0; width: 100%; height: 4px; border-radius: 2px; overflow: hidden;">
                    <div style="background-color: {badge_color}; width: {progress_pct}%; height: 100%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # If it has dialog block, render it
            if "dialog" in item:
                st.markdown(f"""
                <div style="background-color: #EBF3FC; border: 1px solid #BFE3F9; border-radius: 8px; padding: 15px; text-align: left; box-shadow: 0 4px 6px rgba(0, 168, 198, 0.08); margin-bottom: 12px;">
                    <div style="font-weight: 700; color: #1C3D5A; font-size: 13px; margin-bottom: 5px; display: flex; align-items: center; gap: 6px;">
                        <span>⚡</span> Restock Recommendation
                    </div>
                    <div style="font-size: 12px; color: #4A607A; line-height: 1.4; margin-bottom: 8px;">{item["dialog"]["text"]}</div>
                    <div style="font-size: 11px; font-weight: 600; color: #E63946; margin-bottom: 2px;">⏰ {item["dialog"]["timer"]}</div>
                </div>
                """, unsafe_allow_html=True)

                # Interactive Restock Buttons
                btn_yes, btn_no = st.columns(2)
                with btn_yes:
                    if st.button(
                        "Yes",
                        key="alert_restock_yes",
                            use_container_width=True):
                        st.toast(
                            "🤖 AI Replenishment process triggered!", icon="⚡")
                        st.query_params["page"] = "AI_Agent"
                        st.query_params["run"] = "true"
                        st.rerun()
                with btn_no:
                    if st.button(
                        "No",
                        key="alert_restock_no",
                            use_container_width=True):
                        st.toast("Replenishment dialog dismissed.")

        st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------------------
# PAGE B: INVENTORY
# ----------------------------------------------------
elif selected_page == "Inventory":
    df_inv = st.session_state.inventory_db

    # Calculate Dynamic KPI Metrics
    total_items = len(df_inv)
    low_stock = len(df_inv[df_inv["status"] == "LOW STOCK"])
    out_of_stock = len(df_inv[df_inv["status"] == "OUT OF STOCK"])
    healthy = len(df_inv[df_inv["status"] == "HEALTHY"])
    avg_days = round(df_inv["days_left"].mean(), 1)

    # Inventory KPI Cards
    col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
    with col_kpi1:
        st.markdown(
            render_kpi_card(
                "Total SKUs",
                total_items,
                "Across 9 categories",
                "Active Catalog",
                "📦",
                "default"),
            unsafe_allow_html=True)
    with col_kpi2:
        st.markdown(
            render_kpi_card(
                "Low Stock",
                low_stock,
                f"{low_stock} items low",
                "Needs attention",
                "⚠️",
                "yellow"),
            unsafe_allow_html=True)
    with col_kpi3:
        st.markdown(
            render_kpi_card(
                "Out of Stock",
                out_of_stock,
                f"{out_of_stock} items empty",
                "Urgent restock",
                "🚫",
                "red"),
            unsafe_allow_html=True)
    with col_kpi4:
        st.markdown(
            render_kpi_card(
                "Healthy Stock",
                healthy,
                f"{healthy} items safe",
                "Well stocked",
                "✅",
                "green"),
            unsafe_allow_html=True)
    with col_kpi5:
        st.markdown(
            render_kpi_card(
                "Avg. Days Left",
                f"{avg_days}d",
                "All Inventory",
                "Stock coverage",
                "⏱️",
                "purple"),
            unsafe_allow_html=True)

    st.write("")

    # Filters Row
    st.markdown("""
    <style>
    div[data-testid="column"] {
        padding: 0px 5px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_filt_search, col_filt_cat, col_filt_sup, col_filt_stat = st.columns([
                                                                            1.5, 1, 1, 1])

    with col_filt_search:
        search_query = st.text_input(
            "Search bar",
            placeholder="Search by SKU, product, or supplier...",
            label_visibility="collapsed")
    with col_filt_cat:
        categories = ["All Categories"] + \
            sorted(list(df_inv["category"].unique()))
        selected_cat = st.selectbox(
            "Category select",
            categories,
            label_visibility="collapsed")
    with col_filt_sup:
        suppliers = ["All Suppliers"] + \
            sorted(list(df_inv["supplier"].unique()))
        selected_sup = st.selectbox(
            "Supplier select",
            suppliers,
            label_visibility="collapsed")
    with col_filt_stat:
        statuses = [
            "All Statuses",
            "CRITICAL",
            "LOW STOCK",
            "OUT OF STOCK",
            "HEALTHY"]
        selected_stat = st.selectbox(
            "Status select",
            statuses,
            label_visibility="collapsed")

    # Apply Filtering
    df_filtered = df_inv.copy()
    if search_query:
        df_filtered = df_filtered[
            df_filtered["product"].str.contains(search_query, case=False) |
            df_filtered["sku"].str.contains(search_query, case=False) |
            df_filtered["supplier"].str.contains(search_query, case=False)
        ]
    if selected_cat != "All Categories":
        df_filtered = df_filtered[df_filtered["category"] == selected_cat]
    if selected_sup != "All Suppliers":
        df_filtered = df_filtered[df_filtered["supplier"] == selected_sup]
    if selected_stat != "All Statuses":
        df_filtered = df_filtered[df_filtered["status"] == selected_stat]

    # Render Table Header (Grid Layout matching original UI exactly)
    st.markdown("""
    <div style="display: grid; grid-template-columns: 1.15fr 2fr 0.7fr 1.4fr 1.5fr 1.2fr 0.4fr; 
                background-color: #F8FAFC; border: 1px solid #E4EDF5; border-radius: 12px 12px 0 0; 
                font-weight: 600; color: #5B7A9C; font-size: 13px; align-items: center; min-height: 48px;">
        <span style="padding: 12px 16px;">SKU</span>
        <span style="padding: 12px 16px;">Product</span>
        <span style="padding: 12px 16px;">Stock</span>
        <span style="padding: 12px 16px;">Days Left</span>
        <span style="padding: 12px 16px;">Supplier</span>
        <span style="padding: 12px 16px;">Status</span>
        <span style="padding: 12px 16px; text-align: center;">Actions</span>
    </div>
    """, unsafe_allow_html=True)

    # Render Table Rows dynamically
    for _ri, _row in df_filtered.reset_index(drop=True).iterrows():
        _sku = _row['sku']
        _product = _row['product']
        _stock = int(_row['stock'])
        _days_left = float(_row['days_left'])
        _supplier = _row['supplier']
        _status = _row['status']
        _category = _row['category']

        _max_days = 14.0
        _pct = min(100.0, (_days_left / _max_days) * 100.0) if _days_left > 0 else 0.0
        _stock_color = "#EF4444" if _stock == 0 else "#1C3D5A"

        # Days Left bar colour & text
        if _days_left == 0:       _bc, _dc = "#E2E8F0", "#E63946"
        elif _days_left <= 2.0:   _bc, _dc = "#E63946", "#E63946"
        elif _days_left <= 5.0:   _bc, _dc = "#F39C12", "#F39C12"
        else:                      _bc, _dc = "#2ECC71", "#2ECC71"

        # Status badge colours
        _su = _status.upper()
        if _su in ["CRITICAL", "URGENT ORDER"]:  _sbg, _sfg = "#FEE2E2", "#EF4444"
        elif _su == "LOW STOCK":                  _sbg, _sfg = "#FEF3C7", "#D97706"
        elif _su == "HEALTHY":                    _sbg, _sfg = "#D1FAE5", "#10B981"
        elif _su == "OUT OF STOCK":               _sbg, _sfg = "#F3F4F6", "#EF4444"
        else:                                      _sbg, _sfg = "#E0F2FE", "#0369A1"

        _flagged  = st.session_state.get(f"_flag_{_sku}", False)
        _row_bg   = "#FFF7ED" if _flagged else ("#FFFFFF" if _ri % 2 == 0 else "#F8FAFC")
        _flag_border = "border-left:3px solid #F59E0B;" if _flagged else "border-left:3px solid transparent;"

        _c_data, _c_btn = st.columns([12, 1], gap="small")

        with _c_data:
            st.markdown(f"""
            <div style="display:grid; grid-template-columns:1.1fr 2fr 0.7fr 1.4fr 1.5fr 1.2fr;
                         background-color:{_row_bg}; border-bottom:1px solid #E4EDF5;
                         {_flag_border} align-items:center; min-height:54px;">
                <span style="padding:12px 16px; font-family:monospace; font-size:13px;
                              font-weight:500; color:#1C3D5A;">{_sku}</span>
                <span style="padding:12px 16px; font-weight:600; color:#1C3D5A;">
                    {_product}{'&nbsp;🚩' if _flagged else ''}
                </span>
                <span style="padding:12px 16px; font-weight:700; color:{_stock_color};">{_stock}</span>
                <span style="padding:12px 16px;">
                    <span style="display:inline-flex; align-items:center; gap:8px;">
                        <span style="display:inline-block; background:#E2E8F0; width:50px; height:6px;
                                      border-radius:3px; overflow:hidden; vertical-align:middle;">
                            <span style="display:block; background:{_bc}; width:{_pct}%; height:100%;"></span>
                        </span>
                        <span style="color:{_dc}; font-weight:600; font-size:13px;">{_days_left}d</span>
                    </span>
                </span>
                <span style="padding:12px 16px; color:#4A607A;">{_supplier}</span>
                <span style="padding:12px 16px;">
                    <span style="background:{_sbg}; color:{_sfg}; padding:3px 8px; border-radius:6px;
                                  font-size:11px; font-weight:700; text-transform:uppercase;
                                  border:1px solid {_sfg}20;">{_su}</span>
                </span>
            </div>
            """, unsafe_allow_html=True)

        with _c_btn:
            with st.popover("⋮", use_container_width=True):
                st.markdown(f"**{_product}**")
                st.caption(f"`{_sku}` · {_category}")
                st.divider()

                # 👁 View / hide details
                if st.button("👁  View Details", key=f"_vd_{_sku}", use_container_width=True):
                    _k = f"_det_{_sku}"
                    st.session_state[_k] = not st.session_state.get(_k, False)

                # 📦 Request Restock → navigate to AI Agent page
                if st.button("📦  Request Restock", key=f"_rr_{_sku}", use_container_width=True):
                    st.query_params["page"] = "AI_Agent"
                    st.toast(f"📦 Restock request raised for **{_product}**")
                    st.rerun()

                # 🚩 Flag / unflag
                _fl_lbl = "✅  Remove Flag" if _flagged else "🚩  Flag Issue"
                if st.button(_fl_lbl, key=f"_fl_{_sku}", use_container_width=True):
                    st.session_state[f"_flag_{_sku}"] = not _flagged
                    st.toast(f"{'✅ Flag removed' if _flagged else '🚩 Flagged'}: {_product}")

                # ✏️ Toggle inline stock editor
                if st.button("✏️  Edit Stock", key=f"_ed_{_sku}", use_container_width=True):
                    _ek = f"_edit_{_sku}"
                    st.session_state[_ek] = not st.session_state.get(_ek, False)

        # ── Expanded Detail Card ──────────────────────────────────────────────
        if st.session_state.get(f"_det_{_sku}", False):
            st.markdown(f"""
            <div style="background:#EBF3FC; border:1px solid #BFE3F9; border-radius:0 0 8px 8px;
                         padding:14px 20px; margin-bottom:4px; display:grid;
                         grid-template-columns:repeat(5,1fr); gap:12px; font-size:12px;">
                <div><span style="color:#5B7A9C;display:block;font-size:10px;text-transform:uppercase;font-weight:600;">SKU</span>
                     <span style="font-weight:700;color:#1C3D5A;font-family:monospace;">{_sku}</span></div>
                <div><span style="color:#5B7A9C;display:block;font-size:10px;text-transform:uppercase;font-weight:600;">Category</span>
                     <span style="font-weight:700;color:#1C3D5A;">{_category}</span></div>
                <div><span style="color:#5B7A9C;display:block;font-size:10px;text-transform:uppercase;font-weight:600;">Stock</span>
                     <span style="font-weight:700;color:{_stock_color};">{_stock} units</span></div>
                <div><span style="color:#5B7A9C;display:block;font-size:10px;text-transform:uppercase;font-weight:600;">Days Left</span>
                     <span style="font-weight:700;color:{_dc};">{_days_left}d</span></div>
                <div><span style="color:#5B7A9C;display:block;font-size:10px;text-transform:uppercase;font-weight:600;">Supplier</span>
                     <span style="font-weight:700;color:#1C3D5A;">{_supplier}</span></div>
            </div>
            """, unsafe_allow_html=True)

        # ── Inline Stock Edit Form ────────────────────────────────────────────
        if st.session_state.get(f"_edit_{_sku}", False):
            _ec1, _ec2, _ec3, _ec4 = st.columns([1.5, 2.0, 1.0, 0.8])
            with _ec1:
                _new_stock = st.number_input(
                    f"Stock for {_product}",
                    min_value=0, value=_stock, step=1,
                    key=f"_nsi_{_sku}"
                )
            with _ec2:
                _curr_exp = _row.get("expiry_date", "")
                if pd.isna(_curr_exp) or _curr_exp is None:
                    _curr_exp = ""
                _new_expiry = st.text_input(
                    f"Expiry Date (YYYY-MM-DD)",
                    value=str(_curr_exp),
                    key=f"_nei_{_sku}",
                    placeholder="YYYY-MM-DD"
                )
            with _ec3:
                st.write("") # Spacer to align
                st.write("") # Spacer to align
                if st.button("💾 Save", key=f"_sv_{_sku}", use_container_width=True):
                    product_id = int(_sku.split("-")[1])
                    _record_date = _row.get("date", "2026-07-09")
                    try:
                        resp = requests.post(f"{API_BASE_URL}/api/update_inventory", json={
                            "product_id": product_id,
                            "date": _record_date,
                            "current_stock": int(_new_stock),
                            "expiry_date": _new_expiry if _new_expiry.strip() else None
                        }, timeout=10)
                        if resp.status_code == 200:
                            st.toast(f"✅ Saved to database: {_product} ({_new_stock} units)", icon="💾")
                            reload_all_data()
                            if f"_edit_{_sku}" in st.session_state:
                                del st.session_state[f"_edit_{_sku}"]
                            st.rerun()
                        else:
                            st.error(f"Failed to update stock: {resp.text}")
                    except Exception as e:
                        st.error(f"Error connecting to backend: {e}")
            with _ec4:
                st.write("") # Spacer to align
                st.write("") # Spacer to align
                if st.button("✕ Cancel", key=f"_cv_{_sku}", use_container_width=True):
                    if f"_edit_{_sku}" in st.session_state:
                        del st.session_state[f"_edit_{_sku}"]
                    st.rerun()

    # Results summary
    st.markdown(f"""
    <div style="margin-top:10px; font-size:13px; color:#5B7A9C; padding:0 4px;">
        Showing <strong style="color:#1C3D5A;">{len(df_filtered)}</strong>
        of <strong style="color:#1C3D5A;">{len(df_inv)}</strong> inventory items
    </div>
    """, unsafe_allow_html=True)

# ----------------------------------------------------
# PAGE C: DEMAND
# ----------------------------------------------------
elif selected_page == "Demand":
    # 2 Charts Side by Side
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("""
        <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 20px; margin-bottom: 15px;">
            <div style="font-weight: 700; color: #1C3D5A; font-size: 16px; margin-bottom: 2px;">Sales Velocity — 13-Day Trend</div>
            <div style="font-size: 12px; color: #5B7A9C; margin-bottom: 10px;">Units sold per day by category</div>
        </div>
        """, unsafe_allow_html=True)

        # Line chart from demand_data
        df_trend = pd.DataFrame(demand_data.get("sales_velocity_trend", []))
        df_melt = df_trend.melt(
            id_vars=["date"],
            var_name="Category",
            value_name="Units Sold")

        chart_line = alt.Chart(df_melt).mark_line(
            interpolate='monotone',
            strokeWidth=3.5).encode(
            x=alt.X(
                'date:N',
                sort=None,
                title=None),
            y=alt.Y(
                'Units Sold:Q',
                title=None),
            color=alt.Color(
                'Category:N',
                scale=alt.Scale(
                    domain=[
                        'Electronics',
                        'Beverages',
                        'Health',
                        'Fitness'],
                    range=[
                        '#00B4D8',
                        '#4CAF50',
                        '#FF9800',
                        '#9C27B0']),
                title=None)).properties(
            height=260).configure_axis(
            gridOpacity=0.2,
            gridDash=[
                2,
                2],
            labelColor='#8CA0B8').configure_view(
            strokeWidth=0)
        st.altair_chart(chart_line, use_container_width=True)

    with col_chart2:
        st.markdown("""
        <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 20px; margin-bottom: 15px;">
            <div style="font-weight: 700; color: #1C3D5A; font-size: 16px; margin-bottom: 2px;">Daily Volume by Category</div>
            <div style="font-size: 12px; color: #5B7A9C; margin-bottom: 10px;">Jun 19 — Jun 24 volume breakdown</div>
        </div>
        """, unsafe_allow_html=True)

        # Stacked bar chart
        df_vol = pd.DataFrame(demand_data.get("daily_volume_by_category", []))
        chart_bar = alt.Chart(df_vol).mark_bar(
            size=25,
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4).encode(
            x=alt.X(
                'date:N',
                title=None),
            y=alt.Y(
                'volume:Q',
                title=None),
            color=alt.Color(
                'category:N',
                scale=alt.Scale(
                    domain=[
                        'Electronics',
                        'Beverages',
                        'Health',
                        'Fitness'],
                    range=[
                        '#00B4D8',
                        '#4CAF50',
                        '#FF9800',
                        '#9C27B0']),
                title=None)).properties(
            height=260).configure_axis(
            gridOpacity=0.2,
            gridDash=[
                2,
                2],
            labelColor='#8CA0B8').configure_view(
            strokeWidth=0)
        st.altair_chart(chart_bar, use_container_width=True)

    st.write("")

    # Top Velocity SKUs Table
    st.markdown("""
    <div style="font-weight: 700; color: #1C3D5A; font-size: 17px; margin-bottom: 12px;">Top Velocity SKUs</div>
    """, unsafe_allow_html=True)

    # Compile table in HTML
    top_skus = demand_data.get("top_velocity_skus", [])

    html_top = """
    <div style="overflow-x: auto; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E4EDF5; box-shadow: 0 2px 4px rgba(28,61,90,0.01);">
    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
        <thead>
            <tr style="border-bottom: 2px solid #E4EDF5; background-color: #F8FAFC; color: #5B7A9C; font-weight: 600;">
                <th style="padding: 14px 16px;">SKU</th>
                <th style="padding: 14px 16px;">Product</th>
                <th style="padding: 14px 16px;">Category</th>
                <th style="padding: 14px 16px;">Daily Avg</th>
                <th style="padding: 14px 16px;">7-Day Total</th>
                <th style="padding: 14px 16px;">Trend</th>
                <th style="padding: 14px 16px;">Days Remaining</th>
            </tr>
        </thead>
        <tbody>
    """

    for row in top_skus:
        sku = row['sku']
        product = row['product']
        category = row['category']
        daily_avg = row['daily_avg']
        seven_day_total = row['seven_day_total']
        trend = row['trend']
        days_remaining = row['days_remaining']

        progress = render_progress_bar(days_remaining)

        # Color coding for trends
        trend_color = "#10B981" if "+" in trend else "#EF4444"
        arrow = "↑" if "+" in trend else "↓"

        html_top += f"""
            <tr style="border-bottom: 1px solid #E4EDF5; color: #1C3D5A;">
                <td style="padding: 14px 16px; font-weight: 500; font-family: monospace;">{sku}</td>
                <td style="padding: 14px 16px; font-weight: 600; color: #1C3D5A;">{product}</td>
                <td style="padding: 14px 16px; color: #4A607A;">{category}</td>
                <td style="padding: 14px 16px; font-weight: 700; color: #00A8C6;">{daily_avg}</td>
                <td style="padding: 14px 16px; font-weight: 600;">{seven_day_total}</td>
                <td style="padding: 14px 16px; font-weight: 700; color: {trend_color};">{arrow} {trend}</td>
                <td style="padding: 14px 16px;">{progress}</td>
            </tr>
        """

    html_top += """
        </tbody>
    </table>
    </div>
    """
    html_top_wrapped = f"""<!DOCTYPE html><html><head><style>
    {TABLE_BASE_CSS}
    table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
    thead tr {{ background-color: #F8FAFC; border-bottom: 2px solid #E4EDF5; }}
    th {{ padding: 14px 16px; font-weight: 600; color: #5B7A9C; }}
    tbody tr {{ border-bottom: 1px solid #E4EDF5; color: #1C3D5A; }}
    tbody tr:hover {{ background-color: #F8FAFC; }}
    </style></head><body>
    {html_top}
    </body></html>"""
    n_top = len(top_skus)
    components.html(html_top_wrapped, height=68 + n_top * 60, scrolling=False)

    # ── Dead Stock Analysis Panel ──────────────────────────────────────────────
    st.write("")
    st.write("")
    st.markdown("---")
    st.markdown("""
    <div style="font-weight: 700; color: #1C3D5A; font-size: 17px; margin-bottom: 2px;">⚠️ Dead Stock & Markdown Recommendations</div>
    <div style="font-size: 12.5px; color: #5B7A9C; margin-bottom: 15px;">Identify slow-moving stock over a given window and review markdown recommendations to reclaim capital.</div>
    """, unsafe_allow_html=True)
    
    col_d1, col_d2 = st.columns([3, 1])
    with col_d1:
        dead_days = st.slider("Zero Sales Window (Days)", min_value=14, max_value=120, value=90, step=1, key="dead_stock_slider")
    with col_d2:
        st.write("")
        st.write("")
        run_dead_analysis = st.button("🔍 Run Dead Stock Analysis", key="run_dead_stock_btn", use_container_width=True)
        
    dead_stock_list = get_api_data(f"/api/analytics/dead_stock?days={dead_days}", "")
    
    # Fallback mock list if backend is down or returns empty
    if not dead_stock_list:
        dead_stock_list = [
            {"product_id": 1, "sku": "PRD-0001", "product": "Organic Honey", "supplier": "SUP-001", "stock": 45, "units_sold_last_90d": 0, "days_of_history": 90, "is_dead_stock": True, "cost_price": 5.0, "base_price": 8.0, "suggested_markdown_price": 5.60, "holding_cost_exposure": 225.0},
            {"product_id": 4, "sku": "PRD-0004", "product": "Fresh Blueberries", "supplier": "SUP-002", "stock": 100, "units_sold_last_90d": 0, "days_of_history": 90, "is_dead_stock": True, "cost_price": 2.50, "base_price": 4.50, "suggested_markdown_price": 3.15, "holding_cost_exposure": 250.0},
            {"product_id": 8, "sku": "PRD-0008", "product": "Whole Grain Bread", "supplier": "SUP-003", "stock": 10, "units_sold_last_90d": 12, "days_of_history": 90, "is_dead_stock": False, "cost_price": 1.80, "base_price": 3.00, "suggested_markdown_price": None, "holding_cost_exposure": 0.0}
        ]
        
    if dead_stock_list:
        df_dead = pd.DataFrame(dead_stock_list)
        is_dead = df_dead[df_dead["is_dead_stock"] == True]
        total_exposure = is_dead["holding_cost_exposure"].sum() if not is_dead.empty else 0.0
        dead_skus_count = len(is_dead)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown(render_kpi_card("Tied-up Capital (Dead Stock)", f"${total_exposure:,.2f}", f"{dead_skus_count} slow-moving products", "Valued at cost price", "💰", "red"), unsafe_allow_html=True)
        with col_m2:
            st.markdown(render_kpi_card("Markdown Opportunities", f"{dead_skus_count} SKUs", "30% price reduction suggested", "To accelerate sales velocity", "🏷️", "yellow"), unsafe_allow_html=True)
            
        st.write("")
        
        html_dead = """
        <div style="overflow-x: auto; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E4EDF5; box-shadow: 0 2px 4px rgba(28,61,90,0.01);">
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
            <thead>
                <tr style="border-bottom: 2px solid #E4EDF5; background-color: #F8FAFC; color: #5B7A9C; font-weight: 600;">
                    <th style="padding: 14px 16px;">SKU</th>
                    <th style="padding: 14px 16px;">Product</th>
                    <th style="padding: 14px 16px;">Supplier</th>
                    <th style="padding: 14px 16px;">Stock</th>
                    <th style="padding: 14px 16px;">Sold (Window)</th>
                    <th style="padding: 14px 16px;">Holding Cost</th>
                    <th style="padding: 14px 16px;">Markdown Price</th>
                    <th style="padding: 14px 16px;">Status</th>
                </tr>
            </thead>
            <tbody>
        """
        for row in dead_stock_list:
            sku = row['sku']
            product = row['product']
            supplier = row['supplier']
            stock = row['stock']
            sold = row['units_sold_last_90d']
            holding_cost = row['holding_cost_exposure']
            markdown_price = row['suggested_markdown_price']
            is_dead_row = row['is_dead_stock']
            
            badge = render_status_badge("CRITICAL" if is_dead_row else "HEALTHY")
            markdown_str = f"${markdown_price:,.2f}" if markdown_price is not None and pd.notnull(markdown_price) else "N/A"
            
            html_dead += f"""
                <tr style="border-bottom: 1px solid #E4EDF5; color: #1C3D5A; background-color: {'#FFF5F5' if is_dead_row else '#FFFFFF'};">
                     <td style="padding: 14px 16px; font-weight: 500; font-family: monospace;">{sku}</td>
                     <td style="padding: 14px 16px; font-weight: 600; color: #1C3D5A;">{product}</td>
                     <td style="padding: 14px 16px; color: #4A607A;">{supplier}</td>
                     <td style="padding: 14px 16px; font-weight: 700;">{stock}</td>
                     <td style="padding: 14px 16px; font-weight: 600;">{sold}</td>
                     <td style="padding: 14px 16px; font-weight: 700; color: {'#EF4444' if is_dead_row else '#1C3D5A'};">${holding_cost:,.2f}</td>
                     <td style="padding: 14px 16px; font-weight: 700; color: #10B981;">{markdown_str}</td>
                     <td style="padding: 14px 16px;">{badge}</td>
                </tr>
            """
        html_dead += """
            </tbody>
        </table>
        </div>
        """
        html_dead_wrapped = f"""<!DOCTYPE html><html><head><style>
        {TABLE_BASE_CSS}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
        thead tr {{ background-color: #F8FAFC; border-bottom: 2px solid #E4EDF5; }}
        th {{ padding: 14px 16px; font-weight: 600; color: #5B7A9C; }}
        tbody tr {{ border-bottom: 1px solid #E4EDF5; color: #1C3D5A; }}
        tbody tr:hover {{ background-color: #F8FAFC; }}
        </style></head><body>
        {html_dead}
        </body></html>"""
        components.html(html_dead_wrapped, height=80 + len(dead_stock_list) * 58, scrolling=False)

# ----------------------------------------------------
# PAGE D: SUPPLIERS
# ----------------------------------------------------
elif selected_page == "Suppliers":
    # Supplier cards horizontally
    col_sup1, col_sup2, col_sup3, col_sup4, col_sup5 = st.columns(5)

    for idx, sup in enumerate(suppliers_data):
        reliability_color = "#10B981" if sup["reliability"] >= 90 else (
            "#F59E0B" if sup["reliability"] >= 85 else "#EF4444")

        sup_html = f"""
        <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 18px; box-shadow: 0 2px 4px rgba(28,61,90,0.01); display: flex; flex-direction: column; justify-content: space-between;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-weight: 700; color: #1C3D5A; font-size: 15px;">{sup["name"]}</span>
                <span style="background-color: #EBF3FC; color: #00A8C6; padding: 4px; border-radius: 6px; font-size: 12px;">🌐</span>
            </div>
            <div style="margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: #5B7A9C; margin-bottom: 4px;">
                    <span>Reliability</span>
                    <span style="font-weight: 700; color: {reliability_color};">{sup["reliability"]}%</span>
                </div>
                <div style="background-color: #E2E8F0; width: 100%; height: 5px; border-radius: 2.5px; overflow: hidden;">
                    <div style="background-color: {reliability_color}; width: {sup["reliability"]}%; height: 100%;"></div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; border-top: 1px solid #F3F7FA; padding-top: 10px; font-size: 12px;">
                <div>
                    <span style="color: #8CA0B8; display: block; font-size: 10px; font-weight: 600; text-transform: uppercase;">Lead Time</span>
                    <span style="font-weight: 700; color: #1C3D5A;">{sup["lead_time_days"]}d</span>
                </div>
                <div>
                    <span style="color: #8CA0B8; display: block; font-size: 10px; font-weight: 600; text-transform: uppercase;">Pending</span>
                    <span style="font-weight: 700; color: #1C3D5A;">{sup["pending_orders"]}</span>
                </div>
            </div>
            <div style="margin-top: 10px; background-color: #F8FAFC; border-radius: 6px; padding: 6px 10px; text-align: center;">
                <span style="color: #8CA0B8; font-size: 10px; font-weight: 600; text-transform: uppercase; margin-right: 4px;">MTD Spend</span>
                <span style="font-weight: 700; color: #00A8C6; font-size: 13px;">${sup["mtd_spend"]:,}</span>
            </div>
        </div>
        """

        # Place in appropriate column
        if idx == 0:
            col_sup1.markdown(sup_html, unsafe_allow_html=True)
        elif idx == 1:
            col_sup2.markdown(sup_html, unsafe_allow_html=True)
        elif idx == 2:
            col_sup3.markdown(sup_html, unsafe_allow_html=True)
        elif idx == 3:
            col_sup4.markdown(sup_html, unsafe_allow_html=True)
        elif idx == 4:
            col_sup5.markdown(sup_html, unsafe_allow_html=True)

    st.write("")
    st.write("")

    # Bar Chart Supplier Reliability
    st.markdown("""
    <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 20px;">
        <div style="font-weight: 700; color: #1C3D5A; font-size: 16px; margin-bottom: 2px;">Supplier Performance Matrix</div>
        <div style="font-size: 12px; color: #5B7A9C; margin-bottom: 15px;">Vendor reliability comparisons (%)</div>
    </div>
    """, unsafe_allow_html=True)

    df_sup = pd.DataFrame(suppliers_data)
    chart_sup = alt.Chart(df_sup).mark_bar(
        size=35,
        color='#00A8C6',
        cornerRadiusTopLeft=6,
        cornerRadiusTopRight=6).encode(
        x=alt.X(
            'name:N',
            title=None,
            axis=alt.Axis(
                labelAngle=0,
                labelColor='#4A607A',
                labelFontWeight='bold')),
        y=alt.Y(
            'reliability:Q',
            title=None,
            scale=alt.Scale(
                domain=[
                    70,
                    100],
                clamp=True))).properties(
        height=260).configure_axis(
        gridOpacity=0.2,
        gridDash=[
            2,
            2],
        labelColor='#8CA0B8').configure_view(
        strokeWidth=0)
    st.altair_chart(chart_sup, use_container_width=True)

    # ── Supplier Performance Scorecard & Optimization alternatives ─────────────
    st.write("")
    st.write("")
    st.markdown("---")
    st.markdown("""
    <div style="font-weight: 700; color: #1C3D5A; font-size: 17px; margin-bottom: 2px;">🏆 Supplier Performance Scorecard</div>
    <div style="font-size: 12.5px; color: #5B7A9C; margin-bottom: 15px;">Normalized supplier rankings based on 50/50 weighted combination of lead time score and average product cost price.</div>
    """, unsafe_allow_html=True)
    
    scorecard_list = get_api_data("/api/analytics/supplier_scorecard", "")
    if not scorecard_list:
        scorecard_list = [
            {"rank": 1, "supplier_id": "SUP-001", "products_supplied": 8, "avg_lead_time_day": 3.2, "avg_cost_price": 4.50, "lead_time_score": 90.0, "cost_score": 85.0, "supplier_score": 87.5},
            {"rank": 2, "supplier_id": "SUP-002", "products_supplied": 12, "avg_lead_time_day": 4.5, "avg_cost_price": 3.80, "lead_time_score": 75.0, "cost_score": 92.0, "supplier_score": 83.5},
            {"rank": 3, "supplier_id": "SUP-003", "products_supplied": 5, "avg_lead_time_day": 5.0, "avg_cost_price": 5.20, "lead_time_score": 70.0, "cost_score": 78.0, "supplier_score": 74.0}
        ]
        
    if scorecard_list:
        html_sc = """
        <div style="overflow-x: auto; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E4EDF5; box-shadow: 0 2px 4px rgba(28,61,90,0.01);">
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
            <thead>
                <tr style="border-bottom: 2px solid #E4EDF5; background-color: #F8FAFC; color: #5B7A9C; font-weight: 600;">
                    <th style="padding: 14px 16px; text-align: center;">Rank</th>
                    <th style="padding: 14px 16px;">Supplier ID</th>
                    <th style="padding: 14px 16px; text-align: center;">Products Supplied</th>
                    <th style="padding: 14px 16px;">Avg Lead Time</th>
                    <th style="padding: 14px 16px;">Avg Cost Price</th>
                    <th style="padding: 14px 16px;">Lead Time Score</th>
                    <th style="padding: 14px 16px;">Cost Score</th>
                    <th style="padding: 14px 16px; font-weight: 700; color: #00A8C6;">Overall Supplier Score</th>
                </tr>
            </thead>
            <tbody>
        """
        for row in scorecard_list:
            rank = row["rank"]
            sid = row["supplier_id"]
            supplied = row["products_supplied"]
            alt_lt = row["avg_lead_time_day"]
            alt_cp = row["avg_cost_price"]
            lts = row["lead_time_score"]
            cs = row["cost_score"]
            ss = row["supplier_score"]
            
            html_sc += f"""
                <tr style="border-bottom: 1px solid #E4EDF5; color: #1C3D5A;">
                    <td style="padding: 14px 16px; text-align: center; font-weight: 700;">#{rank}</td>
                    <td style="padding: 14px 16px; font-weight: 600;">{sid}</td>
                    <td style="padding: 14px 16px; text-align: center; font-weight: 600;">{supplied}</td>
                    <td style="padding: 14px 16px;">{alt_lt:.1f} days</td>
                    <td style="padding: 14px 16px;">${alt_cp:.2f}</td>
                    <td style="padding: 14px 16px;">{lts:.1f}%</td>
                    <td style="padding: 14px 16px;">{cs:.1f}%</td>
                    <td style="padding: 14px 16px; font-weight: 700; color: #00A8C6;">{ss:.1f}%</td>
                </tr>
            """
        html_sc += """
            </tbody>
        </table>
        </div>
        """
        html_sc_wrapped = f"""<!DOCTYPE html><html><head><style>
        {TABLE_BASE_CSS}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
        thead tr {{ background-color: #F8FAFC; border-bottom: 2px solid #E4EDF5; }}
        th {{ padding: 14px 16px; font-weight: 600; color: #5B7A9C; }}
        tbody tr {{ border-bottom: 1px solid #E4EDF5; color: #1C3D5A; }}
        tbody tr:hover {{ background-color: #F8FAFC; }}
        </style></head><body>
        {html_sc}
        </body></html>"""
        components.html(html_sc_wrapped, height=80 + len(scorecard_list) * 58, scrolling=False)
        
    st.write("")
    st.write("")
    st.markdown("""
    <div style="font-weight: 700; color: #1C3D5A; font-size: 17px; margin-bottom: 2px;">⚡ Supplier Alternatives for At-Risk Items</div>
    <div style="font-size: 12.5px; color: #5B7A9C; margin-bottom: 15px;">Check whether at-risk items (LOW/OUT OF STOCK) could be reordered from a more reliable or cost-effective supplier.</div>
    """, unsafe_allow_html=True)
    
    alt_list = get_api_data("/api/analytics/supplier_alternatives", "")
    if not alt_list:
        alt_list = [
            {"product_id": 2, "sku": "PRD-0002", "product": "Greek Yogurt", "supplier_id": "SUP-003", "current_supplier_score": 74.0, "best_alt_supplier": "SUP-001", "best_alt_supplier_score": 87.5, "better_supplier_available": True, "stock_status": "LOW STOCK", "days_of_stock_left": 1.5}
        ]
        
    better_alts = [x for x in alt_list if x.get("better_supplier_available") == True]
    
    if better_alts:
        html_alts = """
        <div style="overflow-x: auto; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E4EDF5; box-shadow: 0 2px 4px rgba(28,61,90,0.01);">
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
            <thead>
                <tr style="border-bottom: 2px solid #E4EDF5; background-color: #F8FAFC; color: #5B7A9C; font-weight: 600;">
                    <th style="padding: 14px 16px;">SKU</th>
                    <th style="padding: 14px 16px;">Product</th>
                    <th style="padding: 14px 16px;">Stock Status</th>
                    <th style="padding: 14px 16px;">Current Supplier</th>
                    <th style="padding: 14px 16px; text-align: center;">Current Score</th>
                    <th style="padding: 14px 16px; font-weight: 700; color: #10B981;">Recommended Alternative</th>
                    <th style="padding: 14px 16px; text-align: center; font-weight: 700; color: #10B981;">Alternative Score</th>
                </tr>
            </thead>
            <tbody>
        """
        for row in better_alts:
            sku = row['sku']
            product = row['product']
            status = row['stock_status']
            curr_sup = row['supplier_id']
            curr_score = row['current_supplier_score']
            best_alt = row['best_alt_supplier']
            best_score = row['best_alt_supplier_score']
            
            badge = render_status_badge("CRITICAL" if status == "OUT_OF_STOCK" else "LOW STOCK")
            
            html_alts += f"""
                <tr style="border-bottom: 1px solid #E4EDF5; color: #1C3D5A;">
                     <td style="padding: 14px 16px; font-weight: 500; font-family: monospace;">{sku}</td>
                     <td style="padding: 14px 16px; font-weight: 600; color: #1C3D5A;">{product}</td>
                     <td style="padding: 14px 16px;">{badge}</td>
                     <td style="padding: 14px 16px; font-weight: 600; color: #4A607A;">{curr_sup}</td>
                     <td style="padding: 14px 16px; text-align: center; font-weight: 600; color: #E63946;">{curr_score:.1f}%</td>
                     <td style="padding: 14px 16px; font-weight: 700; color: #10B981;">{best_alt} 🌟</td>
                     <td style="padding: 14px 16px; text-align: center; font-weight: 700; color: #10B981;">{best_score:.1f}%</td>
                </tr>
            """
        html_alts += """
            </tbody>
        </table>
        </div>
        """
        html_alts_wrapped = f"""<!DOCTYPE html><html><head><style>
        {TABLE_BASE_CSS}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
        thead tr {{ background-color: #F8FAFC; border-bottom: 2px solid #E4EDF5; }}
        th {{ padding: 14px 16px; font-weight: 600; color: #5B7A9C; }}
        tbody tr {{ border-bottom: 1px solid #E4EDF5; color: #1C3D5A; }}
        tbody tr:hover {{ background-color: #F8FAFC; }}
        </style></head><body>
        {html_alts}
        </body></html>"""
        components.html(html_alts_wrapped, height=80 + len(better_alts) * 58, scrolling=False)
    else:
        st.success("✅ No low-stock items have alternative suppliers with better scorecard ranks.")

# ----------------------------------------------------
# PAGE E: AI AGENT (PROPOSAL)
# ----------------------------------------------------
elif selected_page == "AI_Agent":
    # Simulated Agent Run Execution (Day 5 & 6)
    params = st.query_params
    run_agent = params.get("run", "false") == "true"

    if run_agent:
        placeholder = st.empty()

        steps = [
            {"icon": "🔍", "text": "Querying vector database for procurement policies (RAG)..."},
            {"icon": "⚙️", "text": "Evaluating vendor reliability & historical lead times..."},
            {"icon": "💡", "text": "Running discount analysis & safety stock formulas..."},
            {"icon": "📝", "text": "Generating policy-compliant replenishment proposals..."}
        ]

        for i in range(len(steps)):
            steps_html = ""
            for idx, step in enumerate(steps):
                if idx < i:
                    status_class = "done"
                    indicator = "🟢 Done"
                    step_text = f"✓ {step['text']}"
                elif idx == i:
                    status_class = "active"
                    indicator = "⏳ Running"
                    step_text = f"⚙️ {step['text']}"
                else:
                    status_class = "pending"
                    indicator = "⚪ Pending"
                    step_text = step['text']

                steps_html += f"""
                <div class="loading-step {status_class}">
                    <span style="font-size: 16px;">{step['icon']}</span>
                    <span style="flex-grow: 1;">{step_text}</span>
                    <span style="font-size: 11px; font-weight: bold; text-transform: uppercase;">{indicator}</span>
                </div>
                """

            loading_card_html = f"""
            <div class="spinner-container">
                <div class="spinner"></div>
                <div style="font-weight: 700; font-size: 18px; color: #1C3D5A; margin-bottom: 20px; text-align: center;">StockMind AI Agent Running Analysis</div>
                <div style="width: 100%; display: flex; flex-direction: column; align-items: center;">
                    {steps_html}
                </div>
            </div>
            """
            placeholder.markdown(loading_card_html, unsafe_allow_html=True)

            if i == 2:
                # Actual backend API trigger
                try:
                    res = requests.post(
                        f"{API_BASE_URL}/api/replenish", timeout=60)
                    if res.status_code == 200:
                        st.session_state.agent_proposal = res.json()
                        st.session_state.proposal_db = st.session_state.agent_proposal[
                            "recommendations"]
                    else:
                        st.error(
                            "FastAPI backend failed to process replenishment.")
                except Exception as e:
                    st.error(f"Error calling replenishment API: {e}")
            else:
                time.sleep(0.05)

        # Final step complete render
        steps_html = ""
        for step in steps:
            steps_html += f"""
            <div class="loading-step done">
                <span style="font-size: 16px;">{step['icon']}</span>
                <span style="flex-grow: 1;">✓ {step['text']}</span>
                <span style="font-size: 11px; font-weight: bold; text-transform: uppercase;">🟢 Done</span>
            </div>
            """
        loading_card_html = f"""
        <div class="spinner-container">
            <div class="spinner"></div>
            <div style="font-weight: 700; font-size: 18px; color: #1C3D5A; margin-bottom: 20px; text-align: center;">StockMind AI Agent Running Analysis</div>
            <div style="width: 100%; display: flex; flex-direction: column; align-items: center;">
                {steps_html}
            </div>
        </div>
        """
        placeholder.markdown(loading_card_html, unsafe_allow_html=True)
        time.sleep(0.05)

        placeholder.empty()
        st.query_params["run"] = "false"
        st.rerun()

    agent_proposal = st.session_state.get(
        "agent_proposal", load_mock_json("agent_proposal.json"))
    recs = st.session_state.get(
        "proposal_db",
        agent_proposal["recommendations"])

    # 1. Proposal Banner with interactive re-run button
    col_banner_info, col_banner_btn = st.columns([3.2, 0.8])
    with col_banner_info:
        st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(28,61,90,0.01); height: 85px;">
            <div>
                <div style="font-weight: 700; font-size: 17px; color: #1C3D5A;">AI Replenishment Proposal</div>
                <div style="font-size: 12px; color: #8CA0B8; margin-top: 4px;">Generated: {agent_proposal["timestamp"]} • Confidence: <span style="color: #10B981; font-weight: 700;">{agent_proposal["confidence"]}%</span></div>
            </div>
            <div>
                <span style="background-color: #D1FAE5; color: #10B981; border: 1px solid #10B98130; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; gap: 6px;">
                    ● ANALYSIS COMPLETE
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_banner_btn:
        st.markdown("""
        <style>
        div[data-testid="column"] button {
            background-color: #00A8C6 !important;
            color: white !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            border: none !important;
            height: 85px !important;
            margin-top: 0px !important;
            font-size: 14px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button(
            "⚡ Re-run AI Agent",
            key="run_proposal_analysis_banner",
                use_container_width=True):
            st.query_params["run"] = "true"
            st.rerun()

    # 2. RAG policy context log card
    st.markdown(f"""
    <div style="background-color: #FFF9E6; border: 1px solid #FFE0B2; border-radius: 8px; padding: 15px 20px; display: flex; align-items: flex-start; gap: 15px; margin-bottom: 25px;">
        <div style="font-size: 24px; margin-top: -2px;">📚</div>
        <div>
            <div style="font-weight: 700; color: #D97706; font-size: 12px; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 4px;">RAG POLICY CONTEXT RETRIEVED</div>
            <div style="font-size: 13px; color: #78350F; line-height: 1.5;">{agent_proposal["rag_policy_context"]}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Define tabs for Day 4 task
    tab_orders, tab_report = st.tabs(
        ["📋 Actionable Recommendations", "🧠 AI Executive Report & Reasoning"])

    with tab_orders:
        # Recommendations Header & Action Button
        col_hdr_recs, col_hdr_btn = st.columns([3, 1])
        with col_hdr_recs:
            st.markdown(f"""
            <div style="font-weight: 700; color: #1C3D5A; font-size: 16px; margin-bottom: 12px; margin-top: 4px;">Recommended Orders ({len(recs)} items)</div>
            """, unsafe_allow_html=True)
        with col_hdr_btn:
            if st.button(
                "📥 APPROVE ALL ORDERS",
                key="approve_all",
                use_container_width=True):
                approved_count = 0
                for r_idx, item in enumerate(recs):
                    if not st.session_state.get(f"approved_{item['sku']}", item["approved"]):
                        product_id = int(item['sku'].split("-")[1])
                        try:
                            resp = requests.post(f"{API_BASE_URL}/api/approve_order", json={
                                "product_id": product_id,
                                "quantity": int(item["units"]),
                                "supplier_id": item["supplier"],
                                "notes": item["reason"]
                            }, timeout=5)
                            if resp.status_code == 200:
                                st.session_state.proposal_db[r_idx]["approved"] = True
                                st.session_state[f"approved_{item['sku']}"] = True
                                approved_count += 1
                        except Exception:
                            pass
                st.toast(f"✅ Approved {approved_count} recommended orders on the backend!", icon="📦")
                st.rerun()

        st.write("")

        # Render recommended orders list
        for idx, item in enumerate(recs):
            is_approved = st.session_state.get(
                f"approved_{item['sku']}", item["approved"])
            is_urgent = item["urgency"] == "URGENT ORDER"

            # Color coding state matching
            card_bg = "#FFFFFF" if is_approved else "#F8FAFC"
            card_opacity = "1.0" if is_approved else "0.55"
            border_color = (
                "#EF4444" if is_urgent else "#F59E0B") if is_approved else "#94A3B8"
            badge_bg = (
                "#FEE2E2" if is_urgent else "#FEF3C7") if is_approved else "#E2E8F0"
            badge_fg = (
                "#EF4444" if is_urgent else "#D97706") if is_approved else "#64748B"
            urg_text = item["urgency"] if is_approved else "REJECTED"

            # Render item columns
            col_desc, col_units, col_vendor, col_action_btns = st.columns([
                                                                          5.5, 1.5, 2, 1.5])

            with col_desc:
                st.markdown(f"""
                <div style="border-left: 4px solid {border_color}; background-color: {card_bg}; opacity: {card_opacity}; border-top: 1px solid #E4EDF5; border-right: 1px solid #E4EDF5; border-bottom: 1px solid #E4EDF5; border-radius: 0 8px 8px 0; padding: 14px 16px; min-height: 85px; display: flex; flex-direction: column; justify-content: center;">
                    <div>
                        <span style="background-color: {badge_bg}; color: {badge_fg}; font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 4px; margin-right: 8px; text-transform: uppercase; display: inline-block; vertical-align: middle;">{urg_text}</span>
                        <span style="font-weight: 700; color: #1C3D5A; font-size: 15px; vertical-align: middle;">{item["product"]}</span>
                        <span style="color: #8CA0B8; font-size: 11px; margin-left: 6px; vertical-align: middle; font-family: monospace;">{item["sku"]}</span>
                    </div>
                    <div style="font-size: 12.5px; color: #5B7A9C; line-height: 1.4; margin-top: 5px;">{item["reason"]}</div>
                </div>
                """, unsafe_allow_html=True)

            with col_units:
                st.markdown(f"""
                <div style="background-color: {card_bg}; opacity: {card_opacity}; border-top: 1px solid #E4EDF5; border-bottom: 1px solid #E4EDF5; padding: 14px 10px; min-height: 85px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;">
                    <div style="font-size: 18px; font-weight: 700; color: #1C3D5A;">{item["units"]}</div>
                    <div style="font-size: 11px; color: #5B7A9C;">units</div>
                </div>
                """, unsafe_allow_html=True)

            with col_vendor:
                st.markdown(f"""
                <div style="background-color: {card_bg}; opacity: {card_opacity}; border-top: 1px solid #E4EDF5; border-bottom: 1px solid #E4EDF5; padding: 14px 10px; min-height: 85px; display: flex; flex-direction: column; align-items: flex-start; justify-content: center;">
                    <div style="font-weight: 600; color: #1C3D5A; font-size: 13px; line-height: 1.2;">{item["supplier"]}</div>
                    <div style="font-size: 11px; color: #5B7A9C; margin-top: 4px; display: flex; align-items: center; gap: 4px;">
                        <span>🕒</span> {item["lead_time_days"]} days
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_action_btns:
                # Interactive action buttons
                st.markdown(f"""
                <style>
                .btn-holder-{idx} {{
                    background-color: {card_bg};
                    border-top: 1px solid #E4EDF5;
                    border-bottom: 1px solid #E4EDF5;
                    border-right: 1px solid #E4EDF5;
                    border-radius: 0 8px 8px 0;
                    min-height: 85px;
                    padding: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 6px;
                }}
                </style>
                <div class="btn-holder-{idx}">
                """, unsafe_allow_html=True)

                sub_b1, sub_b2 = st.columns(2)
                with sub_b1:
                    # Approve check button
                    if st.button(
                            "✓",
                            key=f"app_check_{item['sku']}",
                            use_container_width=True,
                            help="Approve Order"):
                        product_id = int(item['sku'].split("-")[1])
                        try:
                            resp = requests.post(f"{API_BASE_URL}/api/approve_order", json={
                                "product_id": product_id,
                                "quantity": int(item["units"]),
                                "supplier_id": item["supplier"],
                                "notes": item["reason"]
                            }, timeout=5)
                            if resp.status_code == 200:
                                st.session_state.proposal_db[idx]["approved"] = True
                                st.session_state[f"approved_{item['sku']}"] = True
                                st.toast(f"✅ Approved & saved order: {item['product']} ({item['units']} units)", icon="📦")
                            else:
                                st.error(f"Failed to approve order: {resp.text}")
                        except Exception as e:
                            st.error(f"Backend connection error: {e}")
                        st.rerun()
                with sub_b2:
                    # Reject cross button
                    if st.button(
                            "✗",
                            key=f"rej_cross_{item['sku']}",
                            use_container_width=True,
                            help="Reject Order"):
                        st.session_state.proposal_db[idx]["approved"] = False
                        st.session_state[f"approved_{item['sku']}"] = False
                        st.toast(f"❌ Rejected: {item['product']}")
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            st.write("")

        # ── Budget-Constrained Procurement Planner ───────────────────────────
        st.write("")
        st.markdown("---")
        st.markdown("""
        <div style="font-weight: 700; color: #1C3D5A; font-size: 17px; margin-bottom: 2px;">💰 Budget-Constrained Procurement Planner</div>
        <div style="font-size: 12.5px; color: #5B7A9C; margin-bottom: 15px;">Simulate available funds and prioritize purchase orders by urgency (stockout timeline).</div>
        """, unsafe_allow_html=True)

        budget_val = st.slider("Procurement Budget ($)", min_value=1000.0, max_value=40000.0, value=15000.0, step=500.0, key="procurement_budget_slider")
        plan_list = get_api_data(f"/api/analytics/reorder_plan?budget={budget_val}", "")

        # Fallback if backend is down
        if not plan_list:
            plan_list = [
                {"sku": "PRD-0002", "product": "Greek Yogurt", "supplier_id": "SUP-003", "stock": 4, "reorder_point": 10.0, "days_left": 1.5, "status": "LOW STOCK", "order_qty": 6, "cost_price": 2.0, "order_cost": 12.0, "order_status": "APPROVED", "cumulative_spend": 12.0}
            ]

        if plan_list:
            df_p = pd.DataFrame(plan_list)
            app_p = df_p[df_p["order_status"] == "APPROVED"]
            def_p = df_p[df_p["order_status"] == "DEFERRED"]
            tot_app = app_p["order_cost"].sum() if not app_p.empty else 0.0
            tot_def = def_p["order_cost"].sum() if not def_p.empty else 0.0

            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                st.markdown(render_kpi_card("Approved Spend", f"${tot_app:,.2f}", f"{len(app_p)} orders approved", f"Out of {len(df_p)} total suggestions", "✅", "green"), unsafe_allow_html=True)
            with col_b2:
                st.markdown(render_kpi_card("Deferred Spend", f"${tot_def:,.2f}", f"{len(def_p)} orders deferred", "Requires higher budget cap", "⏳", "yellow"), unsafe_allow_html=True)
            with col_b3:
                rem_bud = max(0.0, budget_val - tot_app)
                st.markdown(render_kpi_card("Remaining Budget", f"${rem_bud:,.2f}", f"{(tot_app/budget_val)*100:.1f}% budget used", "Safe to allocate elsewhere", "🛡️", "default"), unsafe_allow_html=True)

            st.write("")

            html_plan = """
            <div style="overflow-x: auto; background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E4EDF5; box-shadow: 0 2px 4px rgba(28,61,90,0.01);">
            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
                <thead>
                    <tr style="border-bottom: 2px solid #E4EDF5; background-color: #F8FAFC; color: #5B7A9C; font-weight: 600;">
                        <th style="padding: 14px 16px;">SKU</th>
                        <th style="padding: 14px 16px;">Product</th>
                        <th style="padding: 14px 16px;">Supplier</th>
                        <th style="padding: 14px 16px; text-align: center;">Days Left</th>
                        <th style="padding: 14px 16px; text-align: center;">Order Qty</th>
                        <th style="padding: 14px 16px;">Cost Price</th>
                        <th style="padding: 14px 16px;">Total Cost</th>
                        <th style="padding: 14px 16px; text-align: center;">Status</th>
                    </tr>
                </thead>
                <tbody>
            """
            for row in plan_list:
                sku = row['sku']
                product = row['product']
                supplier = row['supplier_id']
                days = row['days_left']
                qty = row['order_qty']
                cp = row['cost_price']
                cost = row['order_cost']
                ostatus = row['order_status']

                badge = render_status_badge("HEALTHY" if ostatus == "APPROVED" else "LOW STOCK")
                days_str = f"{days:.1f}d" if days < 999 else "N/A"

                html_plan += f"""
                    <tr style="border-bottom: 1px solid #E4EDF5; color: #1C3D5A; background-color: {'#ECFDF5' if ostatus == 'APPROVED' else '#FFFBEB'};">
                        <td style="padding: 14px 16px; font-weight: 500; font-family: monospace;">{sku}</td>
                        <td style="padding: 14px 16px; font-weight: 600; color: #1C3D5A;">{product}</td>
                        <td style="padding: 14px 16px; color: #4A607A;">{supplier}</td>
                        <td style="padding: 14px 16px; text-align: center; font-weight: 600;">{days_str}</td>
                        <td style="padding: 14px 16px; text-align: center; font-weight: 700; color: #00A8C6;">{qty}</td>
                        <td style="padding: 14px 16px;">${cp:.2f}</td>
                        <td style="padding: 14px 16px; font-weight: 700;">${cost:,.2f}</td>
                        <td style="padding: 14px 16px; text-align: center;">{badge}</td>
                    </tr>
                """
            html_plan += """
                </tbody>
            </table>
            </div>
            """
            html_plan_wrapped = f"""<!DOCTYPE html><html><head><style>
            {TABLE_BASE_CSS}
            table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
            thead tr {{ background-color: #F8FAFC; border-bottom: 2px solid #E4EDF5; }}
            th {{ padding: 14px 16px; font-weight: 600; color: #5B7A9C; }}
            tbody tr {{ border-bottom: 1px solid #E4EDF5; color: #1C3D5A; }}
            tbody tr:hover {{ background-color: #F8FAFC; }}
            </style></head><body>
            {html_plan}
            </body></html>"""
            components.html(html_plan_wrapped, height=80 + len(plan_list) * 58, scrolling=False)

    with tab_report:
        col_report_left, col_report_right = st.columns([1.8, 1.2])

        with col_report_left:
            st.markdown(f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px rgba(28, 61, 90, 0.02); min-height: 520px; color: #1C3D5A;">
                <div style="font-size: 18px; font-weight: 700; color: #1C3D5A; border-bottom: 2px solid #E4EDF5; padding-bottom: 12px; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;">
                    <span>📄</span> Procurement Agent Memo
                </div>
            """, unsafe_allow_html=True)
            st.markdown(agent_proposal.get("executive_report", ""))
            st.markdown("</div>", unsafe_allow_html=True)

        with col_report_right:
            st.markdown("""
            <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(28, 61, 90, 0.02); min-height: 520px; color: #1C3D5A;">
                <div style="font-size: 16px; font-weight: 700; color: #1C3D5A; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;">
                    <span>🧠</span> LangGraph Node Tracing
                </div>
            """, unsafe_allow_html=True)

            for node_idx, step in enumerate(
                agent_proposal.get(
                    "cognitive_reasoning_log", [])):
                node_name = step["node"]
                node_msg = step["message"]
                node_step = step["step"]
                node_status = step["status"]

                st.markdown(f"""
                <div style="display: flex; gap: 12px; position: relative; margin-bottom: 18px;">
                    {"<div style='position: absolute; left: 15px; top: 30px; bottom: -30px; width: 2px; background-color: #00A8C630; z-index: 1;'></div>" if node_idx < len(agent_proposal.get("cognitive_reasoning_log", [])) - 1 else ""}
                    <div style="width: 30px; height: 30px; border-radius: 50%; background-color: #EBF3FC; border: 2.5px solid #00A8C6; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: #00A8C6; z-index: 2; flex-shrink: 0;">
                        {node_step}
                    </div>
                    <div style="background-color: #F8FAFC; border: 1px solid #E4EDF5; border-radius: 8px; padding: 12px; width: 100%;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <span style="font-family: monospace; font-weight: 700; font-size: 12px; color: #1C3D5A;">{node_name}</span>
                            <span style="background-color: #D1FAE5; color: #10B981; font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 4px; border: 1px solid #10B98120;">{node_status}</span>
                        </div>
                        <div style="font-size: 11.5px; color: #5B7A9C; line-height: 1.4;">{node_msg}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)


















































































































































































