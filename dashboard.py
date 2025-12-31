
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- 1. Configuration & Theming ---
st.set_page_config(
    page_title="AnalisisSaham Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

ADMIN_PASSWORD = "admin"

# --- 2. Robust Professional CSS ---
st.markdown("""
    <style>
        /* Main App Background */
        .stApp {
            background-color: #f9fafb;
        }

        /* Sidebar Container */
        [data-testid="stSidebar"] {
            background-color: #0f172a !important; /* Deep Navy */
            border-right: 1px solid #1e293b;
        }

        /* Sidebar Text & Labels */
        [data-testid="stSidebar"] .stMarkdown, 
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {
            color: #f1f5f9 !important;
            font-weight: 500;
        }

        /* Highlight Active Menu */
        [data-testid="stSidebar"] .st-at {
            background-color: #1e293b !important;
            border-radius: 4px;
        }

        /* THE FIX: Sidebar Toggle Button Visibility */
        [data-testid="stHeader"] {
            background-color: rgba(255, 255, 255, 0.8);
            border-bottom: 1px solid #e5e7eb;
        }
        
        /* Force the '>' and 'X' buttons to be visible and dark */
        button[kind="header"], button[kind="headerNoContext"] {
            color: #0f172a !important;
            background-color: #f3f4f6 !important;
            border: 1px solid #d1d5db !important;
            border-radius: 8px !important;
        }

        /* Metric Cards */
        div[data-testid="metric-container"] {
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
        }
        
        /* Section Header Styling */
        .page-header {
            font-size: 28px;
            font-weight: 800;
            color: #111827;
            margin-bottom: 30px;
            letter-spacing: -0.025em;
        }

        /* Clean up Streamlit default elements */
        #MainMenu, footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 3. Database Connection ---
@st.cache_resource
def get_db_connection():
    db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    return create_engine(db_url)

engine = get_db_connection()

# --- 4. Data Logic ---
def get_kpi_metrics():
    with engine.connect() as conn:
        res_rev = conn.execute(text("SELECT SUM(amount) FROM transactions WHERE status = 'success'"))
        total_revenue = res_rev.scalar() or 0
        
        res_users = conn.execute(text("SELECT COUNT(DISTINCT user_id) FROM user_quotas"))
        total_users = res_users.scalar() or 0
        
        res_prem = conn.execute(text("SELECT COUNT(*) FROM user_quotas WHERE is_premium = TRUE"))
        premium_users = res_prem.scalar() or 0
        
        res_tx = conn.execute(text("SELECT COUNT(*) as total, SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success FROM transactions"))
        row = res_tx.fetchone()
        tx_rate = (row[1] / row[0] * 100) if row[0] > 0 else 0
        
    return total_revenue, total_users, premium_users, tx_rate

def get_revenue_trend():
    query = "SELECT DATE(created_at) as date, SUM(amount) as revenue FROM transactions WHERE status = 'success' GROUP BY DATE(created_at) ORDER BY date ASC"
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

def get_transactions_data():
    query = "SELECT order_id, user_id, plan_id, amount, status, created_at FROM transactions ORDER BY created_at DESC LIMIT 500"
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

def get_users_data():
    query = "SELECT user_id, username, first_name, last_name, language_code, is_premium, requests_remaining, total_requests, updated_at FROM user_quotas ORDER BY updated_at DESC LIMIT 200"
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn)

# --- 5. Authentication ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center;'>Admin Authentication</h2>", unsafe_allow_html=True)
            pwd = st.text_input("Access Token", type="password")
            if pwd == ADMIN_PASSWORD:
                st.session_state["password_correct"] = True
                st.rerun()
            elif pwd:
                st.error("Invalid token")
        return False
    return True

# --- 6. Main Flow ---
if check_password():
    # Sidebar Setup
    st.sidebar.markdown("<h2 style='color: white; margin-bottom: 20px;'>COMMAND CENTER</h2>", unsafe_allow_html=True)
    selected_menu = st.sidebar.radio(
        "NAVIGATION",
        ["Dashboard Overview", "Transaction History", "User Database", "System Logs"],
        label_visibility="visible"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.caption("System: 🟢 Online")

    # Layout Content
    if selected_menu == "Dashboard Overview":
        st.markdown('<div class="page-header">Business Overview</div>', unsafe_allow_html=True)
        
        rev, users, premium, tx_rate = get_kpi_metrics()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Gross Revenue", f"Rp {rev:,.0f}")
        m2.metric("Total Users", f"{users}")
        m3.metric("Premium Status", f"{premium}")
        m4.metric("Conversion Rate", f"{tx_rate:.1f}%")
        
        st.markdown("<br><h3>Revenue Performance</h3>", unsafe_allow_html=True)
        df_trend = get_revenue_trend()
        if not df_trend.empty:
            fig = px.area(df_trend, x='date', y='revenue', color_discrete_sequence=['#3b82f6'], template="simple_white")
            fig.update_layout(xaxis_title=None, yaxis_title=None, height=400)
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No sales data recorded yet.")

    elif selected_menu == "Transaction History":
        st.markdown('<div class="page-header">Transaction History</div>', unsafe_allow_html=True)
        df_tx = get_transactions_data()
        
        st.dataframe(
            df_tx,
            column_config={
                "created_at": st.column_config.DatetimeColumn("Date", format="D MMM, HH:mm"),
                "amount": st.column_config.NumberColumn("Amount", format="Rp %d"),
            },
            hide_index=True,
            width="stretch"
        )

    elif selected_menu == "User Database":
        st.markdown('<div class="page-header">User Database</div>', unsafe_allow_html=True)
        df_users = get_users_data()
        
        st.dataframe(
            df_users,
            column_config={
                "is_premium": st.column_config.CheckboxColumn("VIP"),
                "requests_remaining": st.column_config.ProgressColumn("Quota", min_value=0, max_value=1000),
                "updated_at": st.column_config.DatetimeColumn("Last Active", format="D MMM YYYY")
            },
            hide_index=True,
            width="stretch"
        )

    elif selected_menu == "System Logs":
        st.markdown('<div class="page-header">System Logs</div>', unsafe_allow_html=True)
        log_file = "app.log"
        if st.button("Flush Logs"):
            open(log_file, 'w').close()
            st.rerun()
            
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                logs = "".join(reversed(f.readlines()[-100:]))
                st.code(logs, language="log")
        else:
            st.warning("Logs empty.")
