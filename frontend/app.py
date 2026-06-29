import streamlit as st
import streamlit.components.v1 as components
import json
import os
import pandas as pd
import altair as alt

# 1. Set Page Configuration
st.set_page_config(
    page_title="StockMind - Replenishment AI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Mock Data Loader Helper
MOCK_DIR = os.path.join(os.path.dirname(__file__), "mock")

def load_mock_json(filename):
    path = os.path.join(MOCK_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    st.error(f"Mock file not found: {filename}")
    return {}

# Load datasets
overview_data = load_mock_json("overview_data.json")
inventory_data = load_mock_json("inventory_data.json")
demand_data = load_mock_json("demand_data.json")
suppliers_data = load_mock_json("suppliers_data.json")
agent_proposal = load_mock_json("agent_proposal.json")

# Initialize session state for mock database persistence (so UI buttons update state)
if "inventory_db" not in st.session_state and inventory_data:
    st.session_state.inventory_db = pd.DataFrame(inventory_data)

if "proposal_db" not in st.session_state and agent_proposal:
    st.session_state.proposal_db = agent_proposal["recommendations"]

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

def render_kpi_card(title, value, change, detail="", icon="📊", card_type="default"):
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
            <span class="badge">5</span>
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
        <a href="?page=AI_Agent" target="_self" class="trigger-btn">
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
        st.markdown(render_kpi_card("Total SKUs", summary["total_skus"]["value"], summary["total_skus"]["change"], "Across 9 categories", "📦", "default"), unsafe_allow_html=True)
    with col_kpi2:
        st.markdown(render_kpi_card("Needs Action", summary["needs_action"]["value"], summary["needs_action"]["change"], summary["needs_action"]["detail"], "⚠️", "yellow"), unsafe_allow_html=True)
    with col_kpi3:
        st.markdown(render_kpi_card("Avg Daily Velocity", summary["avg_velocity"]["value"], summary["avg_velocity"]["change"], summary["avg_velocity"]["detail"], "📈", "green"), unsafe_allow_html=True)
    with col_kpi4:
        st.markdown(render_kpi_card("Avg SKUs", summary["avg_skus"]["value"], summary["avg_skus"]["change"], summary["avg_skus"]["detail"], "⏱️", "default"), unsafe_allow_html=True)
    with col_kpi5:
        st.markdown(render_kpi_card("Critical Alerts", summary["critical_alerts"]["value"], summary["critical_alerts"]["change"], "Urgent attention", "🚨", "red"), unsafe_allow_html=True)
        
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
        df_melt = df_trend.melt(id_vars=["date"], var_name="Category", value_name="Units Sold")
        
        base = alt.Chart(df_melt).encode(
            x=alt.X('date:N', sort=None, title=None),
            y=alt.Y('Units Sold:Q', title=None),
            color=alt.Color('Category:N', scale=alt.Scale(domain=['Electronics', 'Beverages', 'Health', 'Fitness'],
                                                       range=['#00B4D8', '#4CAF50', '#FF9800', '#9C27B0']), legend=None)
        )
        lines = base.mark_line(interpolate='monotone', strokeWidth=3.5)
        areas = base.mark_area(interpolate='monotone', opacity=0.08)
        chart = (areas + lines).properties(height=260).configure_axis(
            gridOpacity=0.2,
            gridDash=[2,2],
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
        components.html(render_table(df_snapshot, is_snapshot=True), height=68 + n_rows_snap * 58, scrolling=False)
        
    with col_alerts:
        # Critical Alerts Panel
        st.markdown("""
        <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 20px; min-height: 520px; display: flex; flex-direction: column;">
            <div style="font-weight: 700; color: #1C3D5A; font-size: 17px; margin-bottom: 15px;">Critical Alerts</div>
        """, unsafe_allow_html=True)
        
        # Alert List rendering
        for item in overview_data.get("alerts", []):
            is_critical = item["status"] == "CRITICAL"
            badge_color = "#E63946" if is_critical else ("#F39C12" if item["status"] == "LOW STOCK" else "#94A3B8")
            badge_bg = "#FEE2E2" if is_critical else ("#FEF3C7" if item["status"] == "LOW STOCK" else "#F3F4F6")
            
            # Draw progress bar for alerts
            progress_pct = min(100.0, (item["days_left"] / 14.0) * 100.0)
            
            # If it has dialog block, render it
            if "dialog" in item:
                st.markdown(f"""
                <div style="border-top: 1px dashed #D5E3F0; margin-top: 15px; padding-top: 15px;">
                    <div style="background-color: #EBF3FC; border: 1px solid #BFE3F9; border-radius: 8px; padding: 15px; text-align: left;">
                        <div style="font-weight: 700; color: #1C3D5A; font-size: 13px; margin-bottom: 5px;">Restock Recommendation</div>
                        <div style="font-size: 12px; color: #4A607A; line-height: 1.4; margin-bottom: 8px;">{item["dialog"]["text"]}</div>
                        <div style="font-size: 11px; font-weight: 600; color: #E63946; margin-bottom: 12px;">⏰ {item["dialog"]["timer"]}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Interactive Restock Buttons
                btn_yes, btn_no = st.columns(2)
                with btn_yes:
                    if st.button("Yes", key="alert_restock_yes", use_container_width=True):
                        st.toast("🤖 AI Replenishment process triggered!", icon="⚡")
                        st.query_params["page"] = "AI_Agent"
                        st.rerun()
                with btn_no:
                    if st.button("No", key="alert_restock_no", use_container_width=True):
                        st.toast("Replenishment dialog dismissed.")
            else:
                st.markdown(f"""
                <div style="background-color: #F8FAFC; border: 1px solid #E4EDF5; border-radius: 8px; padding: 12px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 700; font-size: 13px; color: #1C3D5A; max-width: 140px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{item["product"]}</span>
                        <span style="background-color: {badge_bg}; color: {badge_color}; font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 4px;">{item["status"]}</span>
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
        st.markdown(render_kpi_card("Total SKUs", total_items, "Across 9 categories", "Active Catalog", "📦", "default"), unsafe_allow_html=True)
    with col_kpi2:
        st.markdown(render_kpi_card("Low Stock", low_stock, f"{low_stock} items low", "Needs attention", "⚠️", "yellow"), unsafe_allow_html=True)
    with col_kpi3:
        st.markdown(render_kpi_card("Out of Stock", out_of_stock, f"{out_of_stock} items empty", "Urgent restock", "🚫", "red"), unsafe_allow_html=True)
    with col_kpi4:
        st.markdown(render_kpi_card("Healthy Stock", healthy, f"{healthy} items safe", "Well stocked", "✅", "green"), unsafe_allow_html=True)
    with col_kpi5:
        st.markdown(render_kpi_card("Avg. Days Left", f"{avg_days}d", "All Inventory", "Stock coverage", "⏱️", "purple"), unsafe_allow_html=True)
        
    st.write("")
    
    # Filters Row
    st.markdown("""
    <style>
    div[data-testid="column"] {
        padding: 0px 5px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col_filt_search, col_filt_cat, col_filt_sup, col_filt_stat = st.columns([1.5, 1, 1, 1])
    
    with col_filt_search:
        search_query = st.text_input("Search bar", placeholder="Search by SKU, product, or supplier...", label_visibility="collapsed")
    with col_filt_cat:
        categories = ["All Categories"] + sorted(list(df_inv["category"].unique()))
        selected_cat = st.selectbox("Category select", categories, label_visibility="collapsed")
    with col_filt_sup:
        suppliers = ["All Suppliers"] + sorted(list(df_inv["supplier"].unique()))
        selected_sup = st.selectbox("Supplier select", suppliers, label_visibility="collapsed")
    with col_filt_stat:
        statuses = ["All Statuses", "CRITICAL", "LOW STOCK", "OUT OF STOCK", "HEALTHY"]
        selected_stat = st.selectbox("Status select", statuses, label_visibility="collapsed")
        
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
        
    # Render Table
    n_rows = len(df_filtered)
    components.html(render_table(df_filtered, is_snapshot=False), height=68 + n_rows * 58, scrolling=n_rows > 10)
    
    # Mock Pagination
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; font-size: 13px; color: #5B7A9C; padding: 0 10px;">
        <div>Showing 1 to {len(df_filtered)} of {len(df_filtered)} results</div>
        <div style="display: flex; gap: 6px; align-items: center;">
            <span style="background-color: #BFE3F9; color: #1C3D5A; padding: 4px 10px; border-radius: 4px; font-weight: 700; cursor: pointer;">1</span>
            <span style="background-color: #FFFFFF; border: 1px solid #E4EDF5; color: #4A607A; padding: 4px 10px; border-radius: 4px; cursor: pointer;">2</span>
            <span style="background-color: #FFFFFF; border: 1px solid #E4EDF5; color: #4A607A; padding: 4px 10px; border-radius: 4px; cursor: pointer;">3</span>
            <span>...</span>
            <span style="background-color: #FFFFFF; border: 1px solid #E4EDF5; color: #4A607A; padding: 4px 10px; border-radius: 4px; cursor: pointer;">36</span>
            <span style="background-color: #FFFFFF; border: 1px solid #E4EDF5; color: #4A607A; padding: 4px 8px; border-radius: 4px; cursor: pointer;">&gt;</span>
        </div>
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
        df_melt = df_trend.melt(id_vars=["date"], var_name="Category", value_name="Units Sold")
        
        chart_line = alt.Chart(df_melt).mark_line(interpolate='monotone', strokeWidth=3.5).encode(
            x=alt.X('date:N', sort=None, title=None),
            y=alt.Y('Units Sold:Q', title=None),
            color=alt.Color('Category:N', scale=alt.Scale(domain=['Electronics', 'Beverages', 'Health', 'Fitness'],
                                                       range=['#00B4D8', '#4CAF50', '#FF9800', '#9C27B0']), title=None)
        ).properties(height=260).configure_axis(
            gridOpacity=0.2,
            gridDash=[2,2],
            labelColor='#8CA0B8'
        ).configure_view(
            strokeWidth=0
        )
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
        chart_bar = alt.Chart(df_vol).mark_bar(size=25, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X('date:N', title=None),
            y=alt.Y('volume:Q', title=None),
            color=alt.Color('category:N', scale=alt.Scale(domain=['Electronics', 'Beverages', 'Health', 'Fitness'],
                                                       range=['#00B4D8', '#4CAF50', '#FF9800', '#9C27B0']), title=None)
        ).properties(height=260).configure_axis(
            gridOpacity=0.2,
            gridDash=[2,2],
            labelColor='#8CA0B8'
        ).configure_view(
            strokeWidth=0
        )
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

# ----------------------------------------------------
# PAGE D: SUPPLIERS
# ----------------------------------------------------
elif selected_page == "Suppliers":
    # Supplier cards horizontally
    col_sup1, col_sup2, col_sup3, col_sup4, col_sup5 = st.columns(5)
    
    for idx, sup in enumerate(suppliers_data):
        reliability_color = "#10B981" if sup["reliability"] >= 90 else ("#F59E0B" if sup["reliability"] >= 85 else "#EF4444")
        
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
    chart_sup = alt.Chart(df_sup).mark_bar(size=35, color='#00A8C6', cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
        x=alt.X('name:N', title=None, axis=alt.Axis(labelAngle=0, labelColor='#4A607A', labelFontWeight='bold')),
        y=alt.Y('reliability:Q', title=None, scale=alt.Scale(domain=[70, 100], clamp=True))
    ).properties(height=260).configure_axis(
        gridOpacity=0.2,
        gridDash=[2,2],
        labelColor='#8CA0B8'
    ).configure_view(
        strokeWidth=0
    )
    st.altair_chart(chart_sup, use_container_width=True)

# ----------------------------------------------------
# PAGE E: AI AGENT (PROPOSAL)
# ----------------------------------------------------
elif selected_page == "AI_Agent":
    recs = st.session_state.proposal_db
    
    # 1. Proposal Banner
    st.markdown(f"""
    <div style="background-color: #FFFFFF; border: 1px solid #E4EDF5; border-radius: 12px; padding: 18px 24px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(28,61,90,0.01);">
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
    
    # Recommendations Header & Action Button
    col_hdr_recs, col_hdr_btn = st.columns([3, 1])
    with col_hdr_recs:
        st.markdown(f"""
        <div style="font-weight: 700; color: #1C3D5A; font-size: 16px; margin-bottom: 12px; margin-top: 4px;">Recommended Orders ({len(recs)} items)</div>
        """, unsafe_allow_html=True)
    with col_hdr_btn:
        # Action button to approve all remaining orders
        if st.button("📥 APPROVE ALL ORDERS", key="approve_all", use_container_width=True):
            for item in recs:
                st.session_state[f"approved_{item['sku']}"] = True
            st.toast("✅ Approved all recommended orders!", icon="📦")
            st.rerun()
            
    st.write("")
    
    # Render recommended orders list
    for idx, item in enumerate(recs):
        is_approved = st.session_state.get(f"approved_{item['sku']}", item["approved"])
        is_urgent = item["urgency"] == "URGENT ORDER"
        
        # Color coding state matching
        card_bg = "#FFFFFF" if is_approved else "#F8FAFC"
        card_opacity = "1.0" if is_approved else "0.55"
        border_color = ("#EF4444" if is_urgent else "#F59E0B") if is_approved else "#94A3B8"
        badge_bg = ("#FEE2E2" if is_urgent else "#FEF3C7") if is_approved else "#E2E8F0"
        badge_fg = ("#EF4444" if is_urgent else "#D97706") if is_approved else "#64748B"
        urg_text = item["urgency"] if is_approved else "REJECTED"
        
        # Render item columns
        col_desc, col_units, col_vendor, col_action_btns = st.columns([5.5, 1.5, 2, 1.5])
        
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
                if st.button("✓", key=f"app_check_{item['sku']}", use_container_width=True, help="Approve Order"):
                    st.session_state.proposal_db[idx]["approved"] = True
                    st.session_state[f"approved_{item['sku']}"] = True
                    st.toast(f"✅ Approved: {item['product']}")
                    st.rerun()
            with sub_b2:
                # Reject cross button
                if st.button("✗", key=f"rej_cross_{item['sku']}", use_container_width=True, help="Reject Order"):
                    st.session_state.proposal_db[idx]["approved"] = False
                    st.session_state[f"approved_{item['sku']}"] = False
                    st.toast(f"❌ Rejected: {item['product']}")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
        st.write("")
