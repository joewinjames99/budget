import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from pathlib import Path
import json
import uuid
import plotly.graph_objects as go
from collections import Counter
import gspread
from google.oauth2.service_account import Credentials
import warnings

warnings.filterwarnings("ignore")

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Money Hub 💸",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = Path(".data")
DATA_DIR.mkdir(exist_ok=True)
TX_FILE = DATA_DIR / "transactions.json"
BUDGETS_FILE = DATA_DIR / "budgets.json"
GOALS_FILE = DATA_DIR / "goals.json"
THEME_FILE = DATA_DIR / "theme.json"

SHEET_2025_TAB = "2025"
TX_TAB = "Transactions"

DEFAULT_CATEGORIES = [
    "Rent", "Electricity", "Wifi", "Gas", "Phone Bill", "Student Loans",
    "Groceries", "Public Trans.", "Lyft/Ubers", "Subscriptions", "Eating Out",
    "Personal Stuff", "Credits", "Emergency Fund", "Savings", "Shopping", "Health", "Entertainment"
]

SPENDING_CATEGORIES = [
    "Groceries", "Public Trans.", "Lyft/Ubers", "Subscriptions",
    "Eating Out", "Personal Stuff", "Credits", "Shopping", "Health", "Entertainment"
]

FIXED_EXPENSES = [
    "Rent", "Electricity", "Wifi", "Gas", "Phone Bill", "Student Loans",
    "Emergency Fund", "Savings"
]

INCOME_CATEGORIES = ["Paycheck", "Other Income", "Gift", "Refund", "Bonus"]

NEEDS = ["Rent", "Electricity", "Wifi", "Gas", "Phone Bill", "Student Loans", "Groceries", "Health"]
WANTS = ["Eating Out", "Entertainment", "Shopping", "Personal Stuff", "Subscriptions"]

CATEGORY_COLORS = {
    "Rent": "#8b5cf6", "Electricity": "#f59e0b", "Wifi": "#06b6d4", "Gas": "#ef4444",
    "Phone Bill": "#f97316", "Student Loans": "#d946ef",
    "Groceries": "#10b981", "Public Trans.": "#a855f7", "Lyft/Ubers": "#8b5cf6",
    "Subscriptions": "#f59e0b", "Eating Out": "#fb7185", "Personal Stuff": "#ec4899",
    "Credits": "#22c55e", "Emergency Fund": "#14b8a6", "Savings": "#06b6d4",
    "Shopping": "#f472b6", "Health": "#ef4444", "Entertainment": "#a78bfa",
    "Paycheck": "#10b981", "Other Income": "#34d399", "Gift": "#fbbf24",
    "Refund": "#06b6d4", "Bonus": "#f43f5e"
}

# ============================================================
# MODERN CLEAN STYLES
# ============================================================
st.markdown("""
<style>
* { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

.block-container { 
    padding-top: 1rem; 
    padding-bottom: 2rem; 
    max-width: 1600px; 
}

[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    color: #e2e8f0;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%);
}

h1, h2, h3 { 
    letter-spacing: -0.02em; 
    color: #f1f5f9;
    font-weight: 800;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid rgba(59, 130, 246, 0.2);
}

.card {
    border: 1px solid rgba(148, 163, 184, 0.15);
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(51, 65, 85, 0.6) 100%);
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.5);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.card:hover {
    transform: translateY(-2px);
    border-color: rgba(59, 130, 246, 0.3);
    box-shadow: 0 15px 40px rgba(59, 130, 246, 0.15);
}

.kpi-label { 
    opacity: 0.6; 
    font-size: 0.75rem; 
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #94a3b8;
    font-weight: 700;
    margin-bottom: 4px;
}

.kpi-value { 
    font-size: 1.8rem; 
    font-weight: 800;
    color: #f1f5f9;
    margin-bottom: 2px;
}

.kpi-sub { 
    opacity: 0.6; 
    font-size: 0.8rem; 
    color: #cbd5e1;
}

.section-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 12px;
}

.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
    border: 1px solid rgba(59, 130, 246, 0.2);
    background: rgba(59, 130, 246, 0.1);
    color: #93c5fd;
    font-weight: 600;
    margin-right: 6px;
}

.progress-bar {
    height: 6px;
    background: rgba(148, 163, 184, 0.1);
    border-radius: 999px;
    overflow: hidden;
    margin-top: 8px;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #3b82f6, #1d4ed8);
    border-radius: 999px;
    transition: width 0.3s ease;
}

.warning-box {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 8px;
    padding: 10px 12px;
    color: #fca5a5;
    font-size: 0.85rem;
}

.success-box {
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.2);
    border-radius: 8px;
    padding: 10px 12px;
    color: #86efac;
    font-size: 0.85rem;
}

.info-box {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: 8px;
    padding: 10px 12px;
    color: #93c5fd;
    font-size: 0.85rem;
}

hr { 
    border: none; 
    height: 1px; 
    background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.1), transparent); 
    margin: 12px 0; 
}

.stButton > button {
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    border: 1px solid rgba(59, 130, 246, 0.3) !important;
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25) !important;
}

.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4) !important;
}

[data-baseweb="input"] > div, [data-baseweb="select"] > div {
    border-radius: 8px !important;
    background-color: rgba(30, 41, 59, 0.8) !important;
    border-color: rgba(148, 163, 184, 0.15) !important;
}

[data-testid="stExpander"] {
    border: 1px solid rgba(148, 163, 184, 0.1) !important;
    border-radius: 8px !important;
    background: rgba(30, 41, 59, 0.4) !important;
}

[data-testid="stDataFrame"] {
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# HELPERS
# ============================================================
def month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"

def fmt_month(k: str) -> str:
    return datetime.strptime(k + "-01", "%Y-%m-%d").strftime("%B %Y")

def get_month_metrics(df_month, df_all, sel_month, today):
    income = df_month[df_month["Type"].str.lower() == "income"]["Amount"].sum() if not df_month.empty else 0.0
    expenses = df_month[df_month["Type"].str.lower().isin(["expense", "spending"])]["Amount"].sum() if not df_month.empty else 0.0
    fixed_spend = df_month[df_month["Category"].isin(FIXED_EXPENSES)]["Amount"].sum() if not df_month.empty else 0.0
    flex_spend = expenses - fixed_spend
    needs = df_month[df_month["Category"].isin(NEEDS)]["Amount"].sum() if not df_month.empty else 0.0
    wants = df_month[df_month["Category"].isin(WANTS)]["Amount"].sum() if not df_month.empty else 0.0
    net = income - expenses
    
    savings_rate = ((income - expenses) / income * 100) if income > 0 else 0
    fixed_pct = (fixed_spend / income * 100) if income > 0 else 0
    avg_tx = (expenses / len(df_month)) if len(df_month) > 0 else 0
    
    days_in_month = (today.replace(day=28) + timedelta(days=4)).day
    day_of_month = today.day
    days_remaining = max(1, days_in_month - day_of_month)
    
    safe_to_spend = max(0, (income - fixed_spend) - flex_spend)
    daily_safe = safe_to_spend / days_remaining if days_remaining > 0 else safe_to_spend
    
    days_elapsed = max(1, day_of_month)
    daily_spend = expenses / days_elapsed
    projected_month = daily_spend * days_in_month
    
    expected_pct = (day_of_month / days_in_month) * 100
    
    return {
        "income": income, "expenses": expenses, "fixed_spend": fixed_spend,
        "flex_spend": flex_spend, "needs": needs, "wants": wants, "net": net,
        "savings_rate": savings_rate, "fixed_pct": fixed_pct, "avg_tx": avg_tx,
        "safe_to_spend": safe_to_spend, "daily_safe": daily_safe,
        "daily_spend": daily_spend, "projected_month": projected_month,
        "expected_pct": expected_pct, "day_of_month": day_of_month,
        "days_in_month": days_in_month, "days_remaining": days_remaining,
    }

def detect_subscriptions(df_all):
    if df_all.empty:
        return []
    df_t = df_all.copy()
    df_t["YearMonth"] = df_t["Date"].apply(lambda d: month_key(d))
    merchants = df_t["Merchant"].unique()
    subs = []
    for merchant in merchants:
        if merchant.strip() == "" or merchant == "Budget 2025":
            continue
        m_data = df_t[df_t["Merchant"] == merchant]
        months_seen = m_data["YearMonth"].nunique()
        if months_seen >= 2:
            avg_amt = m_data["Amount"].mean()
            subs.append({"merchant": merchant, "months": months_seen, "avg": avg_amt})
    return sorted(subs, key=lambda x: x["months"], reverse=True)

# ============================================================
# THEME MANAGEMENT
# ============================================================
DEFAULT_THEME = {
    "bg_primary": "#fdf2f8",
    "bg_secondary": "#fce7f3",
    "text_primary": "#be185d",
    "text_secondary": "#9f1239",
    "accent": "#ec4899",
    "accent_dark": "#be185d",
}

def load_theme() -> dict:
    if THEME_FILE.exists():
        try:
            return json.loads(THEME_FILE.read_text())
        except:
            return DEFAULT_THEME.copy()
    return DEFAULT_THEME.copy()

def save_theme(theme: dict) -> None:
    with open(THEME_FILE, "w") as f:
        json.dump(theme, f, indent=2)

def apply_theme(theme: dict):
    """Apply theme colors to the app dynamically"""
    bg_primary = theme.get("bg_primary", "#fdf2f8")
    bg_secondary = theme.get("bg_secondary", "#fce7f3")
    text_primary = theme.get("text_primary", "#be185d")
    text_secondary = theme.get("text_secondary", "#9f1239")
    accent = theme.get("accent", "#ec4899")
    accent_dark = theme.get("accent_dark", "#be185d")
    
    st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(135deg, {bg_primary} 0%, {bg_secondary} 50%, {bg_primary} 100%);
        color: {text_primary};
    }}
    
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, rgba(253, 242, 248, 0.95) 0%, rgba(252, 231, 243, 0.95) 100%);
    }}
    
    h1, h2, h3 {{ 
        color: {text_primary};
    }}
    
    .card {{
        border: 1px solid rgba(236, 72, 153, 0.2);
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(252, 231, 243, 0.8) 100%);
    }}
    
    .card:hover {{
        border-color: rgba(236, 72, 153, 0.4);
        box-shadow: 0 15px 40px rgba(236, 72, 153, 0.15);
    }}
    
    .kpi-label {{ 
        color: {text_secondary};
    }}
    
    .kpi-value {{ 
        color: {text_primary};
    }}
    
    .kpi-sub {{ 
        color: {text_secondary};
    }}
    
    .section-title {{
        color: {text_primary};
    }}
    
    .stButton > button {{
        background: linear-gradient(135deg, {accent} 0%, {accent_dark} 100%) !important;
        border-color: rgba(236, 72, 153, 0.3) !important;
        box-shadow: 0 4px 12px rgba(236, 72, 153, 0.25) !important;
    }}
    
    .stButton > button:hover {{
        box-shadow: 0 6px 20px rgba(236, 72, 153, 0.35) !important;
    }}
    
    [data-baseweb="input"] > div, [data-baseweb="select"] > div {{
        border-radius: 8px !important;
        background-color: rgba(255, 255, 255, 0.85) !important;
        border-color: rgba(236, 72, 153, 0.15) !important;
    }}
    
    [data-baseweb="input"] input, [data-baseweb="select"] div {{
        color: {text_primary} !important;
    }}
    
    .progress-fill {{
        background: linear-gradient(90deg, {accent}, {accent_dark});
    }}
    
    hr {{ 
        background: linear-gradient(90deg, transparent, rgba(236, 72, 153, 0.2), transparent);
    }}
    </style>
    """, unsafe_allow_html=True)

# ============================================================
# GOOGLE SHEETS & DATA
# ============================================================
@st.cache_resource
def gs_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def read_2025_budget_matrix() -> pd.DataFrame:
    gc = gs_client()
    sheet_id = st.secrets["GSHEET_ID"]
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(SHEET_2025_TAB)
    return parse_2025_tab(ws.get_all_values())

def parse_2025_tab(raw_data: list) -> pd.DataFrame:
    if not raw_data or len(raw_data) < 2:
        return pd.DataFrame(columns=["Date", "Amount", "Type", "Category", "Merchant", "Notes"])
    header_row_idx = None
    for i, row in enumerate(raw_data):
        if any("2025" in str(cell) for cell in row):
            header_row_idx = i
            break
    if header_row_idx is None:
        return pd.DataFrame(columns=["Date", "Amount", "Type", "Category", "Merchant", "Notes"])
    header_row = raw_data[header_row_idx]
    month_names = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    months, month_cols = [], []
    for col_idx, cell in enumerate(header_row):
        s = str(cell).strip()
        if ("2025" in s) and any(m in s for m in month_names):
            months.append(s)
            month_cols.append(col_idx)
    if not months:
        return pd.DataFrame(columns=["Date", "Amount", "Type", "Category", "Merchant", "Notes"])
    tx = []
    for row_idx in range(header_row_idx + 1, len(raw_data)):
        row = raw_data[row_idx]
        if not row or len(row) <= 2:
            continue
        category = str(row[2]).strip()
        if not category or category in {"INCOME:", "SPENDING:", "EXPENSES:", "SAVINGS", "TOTAL SAVED"}:
            continue
        tx_type = "Income" if category == "INCOME" else ("Spending" if category in SPENDING_CATEGORIES else "Expense")
        for month_str, col_idx in zip(months, month_cols):
            if col_idx >= len(row):
                continue
            amount_str = str(row[col_idx]).strip()
            if not amount_str:
                continue
            try:
                amount = float(amount_str.replace("$","").replace(",",""))
                month_date = datetime.strptime(month_str.strip(), "%B %Y")
                tx.append({
                    "Date": month_date.replace(day=1).date(),
                    "Amount": amount,
                    "Type": tx_type,
                    "Category": category,
                    "Merchant": "Budget 2025",
                    "Notes": ""
                })
            except:
                continue
    return pd.DataFrame(tx) if tx else pd.DataFrame(columns=["Date","Amount","Type","Category","Merchant","Notes"])

def load_budgets() -> dict:
    if BUDGETS_FILE.exists():
        try:
            return json.loads(BUDGETS_FILE.read_text())
        except:
            return {}
    return {}

def save_budgets(budgets: dict) -> None:
    with open(BUDGETS_FILE, "w") as f:
        json.dump(budgets, f, indent=2)

def load_goals() -> list:
    if GOALS_FILE.exists():
        try:
            return json.loads(GOALS_FILE.read_text())
        except:
            return []
    return []

def save_goals(goals: list) -> None:
    with open(GOALS_FILE, "w") as f:
        json.dump(goals, f, indent=2)

def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["ID", "Date", "Amount", "Type", "Category", "Merchant", "Notes"])

def save_transactions(df: pd.DataFrame) -> None:
    out = df.copy()
    out["Date"] = out["Date"].astype(str)
    with open(TX_FILE, "w") as f:
        json.dump(out.to_dict(orient="records"), f, indent=2)

def load_transactions() -> pd.DataFrame:
    if TX_FILE.exists() and TX_FILE.stat().st_size > 0:
        try:
            data = json.loads(TX_FILE.read_text())
            df = pd.DataFrame(data)
            if not df.empty:
                df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
                df["Type"] = df.get("Type", "Expense").fillna("Expense")
                df["Category"] = df.get("Category", "Other").fillna("Other")
                df["Merchant"] = df.get("Merchant", "").fillna("")
                df["Notes"] = df.get("Notes", "").fillna("")
                return df[["ID","Date","Amount","Type","Category","Merchant","Notes"]]
        except:
            pass
    with st.spinner("✨ Loading from Google Sheets…"):
        sheet_df = read_2025_budget_matrix()
        if sheet_df is None or sheet_df.empty:
            return _empty_df()
        sheet_df["ID"] = [str(uuid.uuid4()) for _ in range(len(sheet_df))]
        sheet_df["Amount"] = pd.to_numeric(sheet_df["Amount"], errors="coerce").fillna(0.0)
        sheet_df["Date"] = pd.to_datetime(sheet_df["Date"], errors="coerce").dt.date
        sheet_df["Type"] = sheet_df.get("Type", "Expense").fillna("Expense")
        sheet_df["Category"] = sheet_df.get("Category", "Other").fillna("Other")
        sheet_df["Merchant"] = sheet_df.get("Merchant", "").fillna("")
        sheet_df["Notes"] = sheet_df.get("Notes", "").fillna("")
        save_transactions(sheet_df[["ID","Date","Amount","Type","Category","Merchant","Notes"]])
        return sheet_df[["ID","Date","Amount","Type","Category","Merchant","Notes"]]

def write_to_sheet(df_new: pd.DataFrame) -> None:
    gc = gs_client()
    sh = gc.open_by_key(st.secrets["GSHEET_ID"])
    ws = sh.worksheet(TX_TAB)
    for _, r in df_new.iterrows():
        ws.append_row([str(r["Date"]), float(r["Amount"]), str(r["Type"]), str(r["Category"]), str(r["Merchant"]), str(r["Notes"])])

def add_transaction(df: pd.DataFrame, row: dict) -> pd.DataFrame:
    row["ID"] = row.get("ID") or str(uuid.uuid4())
    new_row = pd.DataFrame([row])
    new_row["Date"] = pd.to_datetime(new_row["Date"]).dt.date
    new_row["Amount"] = pd.to_numeric(new_row["Amount"]).fillna(0.0)
    df2 = pd.concat([df, new_row], ignore_index=True)
    save_transactions(df2)
    try:
        write_to_sheet(new_row)
        st.toast("Synced ✨")
    except:
        st.toast("Saved locally ⚠️")
    return df2

# ============================================================
# SIDEBAR & NAVIGATION
# ============================================================
st.session_state.setdefault("tx_df", load_transactions())
st.session_state.setdefault("budgets", load_budgets())
st.session_state.setdefault("goals", load_goals())
st.session_state.setdefault("theme", load_theme())
df_all = st.session_state["tx_df"].copy()

# Apply theme
apply_theme(st.session_state["theme"])

today = date.today()
months = sorted({month_key(d) for d in df_all["Date"].dropna().tolist() if pd.notna(d)})
cur_m = month_key(today)
if cur_m not in months:
    months.append(cur_m)
months = sorted(months, reverse=True)

with st.sidebar:
    st.markdown("## 💸 Money Hub")
    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
    
    sel_month = st.selectbox("📅 Month", months, index=0, format_func=fmt_month)
    
    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
    
    page = st.radio("Navigation", ["Dashboard", "Budgets", "Goals", "Subscriptions", "Transactions"], label_visibility="collapsed")
    
    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.session_state["tx_df"] = load_transactions()
        st.rerun()
    
    st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
    
    with st.expander("⚙️ Settings"):
        st.markdown("#### 🎨 Theme Colors")
        
        theme = st.session_state["theme"]
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Background**")
            bg_primary = st.color_picker("Primary BG", theme.get("bg_primary", "#fdf2f8"), key="bg_primary")
            bg_secondary = st.color_picker("Secondary BG", theme.get("bg_secondary", "#fce7f3"), key="bg_secondary")
        
        with col_b:
            st.markdown("**Text**")
            text_primary = st.color_picker("Primary Text", theme.get("text_primary", "#be185d"), key="text_primary")
            text_secondary = st.color_picker("Secondary Text", theme.get("text_secondary", "#9f1239"), key="text_secondary")
        
        st.markdown("**Accent**")
        col_c, col_d = st.columns(2)
        with col_c:
            accent = st.color_picker("Accent Color", theme.get("accent", "#ec4899"), key="accent")
        with col_d:
            accent_dark = st.color_picker("Accent Dark", theme.get("accent_dark", "#be185d"), key="accent_dark")
        
        if st.button("💾 Save Theme", use_container_width=True):
            new_theme = {
                "bg_primary": bg_primary,
                "bg_secondary": bg_secondary,
                "text_primary": text_primary,
                "text_secondary": text_secondary,
                "accent": accent,
                "accent_dark": accent_dark,
            }
            save_theme(new_theme)
            st.session_state["theme"] = new_theme
            st.success("Theme saved! Refresh to apply.")
        
        if st.button("🔄 Reset to Default", use_container_width=True):
            save_theme(DEFAULT_THEME.copy())
            st.session_state["theme"] = DEFAULT_THEME.copy()
            st.success("Theme reset!")

# Get month data
df_month = df_all[df_all["Date"].apply(lambda d: month_key(d) == sel_month if pd.notna(d) else False)].copy()
if df_month.empty:
    df_month = _empty_df()

metrics = get_month_metrics(df_month, df_all, sel_month, today)

# ============================================================
# PAGE: DASHBOARD
# ============================================================
if page == "Dashboard":
    st.markdown(f"<div class='section-title'>📊 {fmt_month(sel_month)}</div>", unsafe_allow_html=True)
    
    # Top KPIs
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-label'>💰 Income</div><div class='kpi-value'>${:,.0f}</div>".format(metrics['income']), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with k2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-label'>💸 Expenses</div><div class='kpi-value'>${:,.0f}</div>".format(metrics['expenses']), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with k3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-label'>🎯 Safe to Spend</div><div class='kpi-value'>${:,.0f}</div>".format(metrics['safe_to_spend']), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with k4:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-label'>📊 Net</div><div class='kpi-value'>${:,.0f}</div>".format(metrics['net']), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<hr/>", unsafe_allow_html=True)
    
    # Safe to Spend insights
    st.markdown("### 💚 Spending Status")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Daily Budget</div><div class='kpi-value'>${metrics['daily_safe']:,.0f}</div><div class='kpi-sub'>{metrics['days_remaining']} days left</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_b:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Spending Pace</div><div class='kpi-value'>${metrics['daily_spend']:,.0f}/day</div><div class='kpi-sub'>Projected: ${metrics['projected_month']:,.0f}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    if metrics['safe_to_spend'] < 0:
        st.markdown("<div class='warning-box'>🚨 Already spent your flexible budget</div>", unsafe_allow_html=True)
    elif metrics['projected_month'] > metrics['income']:
        st.markdown(f"<div class='warning-box'>⚠️ On pace to overspend by ${metrics['projected_month'] - metrics['income']:,.0f}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='success-box'>✓ You're in control!</div>", unsafe_allow_html=True)
    
    st.markdown("<hr/>", unsafe_allow_html=True)
    
    # Breakdown
    st.markdown("### 📊 Breakdown")
    col_chart, col_stats = st.columns([2, 1])
    
    with col_chart:
        exp_data = df_month[df_month["Type"].str.lower().isin(["expense", "spending"])].copy()
        if not exp_data.empty:
            by_cat = exp_data.groupby("Category")["Amount"].sum().sort_values(ascending=False)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=by_cat.index, x=by_cat.values, orientation='h',
                marker_color=[CATEGORY_COLORS.get(cat, "#64748b") for cat in by_cat.index],
                text=[f"${v:.0f}" for v in by_cat.values], textposition="auto"
            ))
            fig.update_layout(height=350, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"), margin=dict(l=80, r=0, t=0, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    with col_stats:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Savings Rate</div><div class='kpi-value'>{metrics['savings_rate']:.0f}%</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card' style='margin-top: 8px;'>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Avg Transaction</div><div class='kpi-value'>${metrics['avg_tx']:.0f}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='card' style='margin-top: 8px;'>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>Transactions</div><div class='kpi-value'>{len(df_month)}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<hr/>", unsafe_allow_html=True)
    
    # Quick add
    st.markdown("### ➕ Add Transaction")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        t_date = st.date_input("Date", value=today, label_visibility="collapsed")
    with c2:
        t_type = st.selectbox("Type", ["Expense", "Spending", "Income"], label_visibility="collapsed")
    with c3:
        if t_type == "Income":
            t_cat = st.selectbox("Category", INCOME_CATEGORIES, label_visibility="collapsed")
        elif t_type == "Spending":
            t_cat = st.selectbox("Category", SPENDING_CATEGORIES, label_visibility="collapsed")
        else:
            t_cat = st.selectbox("Category", FIXED_EXPENSES, label_visibility="collapsed")
    with c4:
        t_amt = st.number_input("Amount", min_value=0.0, step=5.0, label_visibility="collapsed")
    
    t_merchant = st.text_input("Merchant", label_visibility="collapsed", key="add_merchant")
    t_notes = st.text_input("Notes", label_visibility="collapsed", key="add_notes")
    
    if st.button("💾 Save Transaction", use_container_width=True):
        if t_amt > 0:
            new = {"Date": str(t_date), "Amount": float(t_amt), "Type": t_type, "Category": t_cat, "Merchant": t_merchant, "Notes": t_notes}
            st.session_state["tx_df"] = add_transaction(st.session_state["tx_df"], new)
            st.rerun()

# ============================================================
# PAGE: BUDGETS
# ============================================================
elif page == "Budgets":
    st.markdown("### 🎯 Budget Board")
    
    budgets = st.session_state.get("budgets", {})
    
    if not budgets:
        st.info("No budgets set. Add one below to get started!")
    else:
        for cat, limit in budgets.items():
            spent = df_month[df_month["Type"].str.lower().isin(["expense","spending"])]["Amount"].sum() if cat == "All" else df_month[df_month["Category"] == cat]["Amount"].sum()
            pct = min(100, (spent / limit * 100)) if limit > 0 else 0
            remaining = max(0, limit - spent)
            
            col_info, col_manage = st.columns([4, 1])
            
            with col_info:
                st.markdown(f"""
                <div class='card'>
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>
                        <span style='font-weight: 700; color: #f1f5f9;'>{cat}</span>
                        <span style='color: #94a3b8;'>${spent:,.0f} / ${limit:,.0f}</span>
                    </div>
                    <div class='progress-bar'><div class='progress-fill' style='width: {pct}%;'></div></div>
                    <div style='margin-top: 8px; display: flex; justify-content: space-between;'>
                        <span class='kpi-sub'>${remaining:,.0f} remaining ({100-pct:.0f}%)</span>
                """, unsafe_allow_html=True)
                
                if pct > metrics['expected_pct'] + 10:
                    st.markdown("<span style='color: #fca5a5; font-size: 0.8rem;'>🚨 Too fast</span>", unsafe_allow_html=True)
                elif pct < metrics['expected_pct'] - 10:
                    st.markdown("<span style='color: #86efac; font-size: 0.8rem;'>✓ Ahead</span>", unsafe_allow_html=True)
                
                st.markdown("</div></div>", unsafe_allow_html=True)
            
            with col_manage:
                if st.button("❌", key=f"del_{cat}", use_container_width=True):
                    del budgets[cat]
                    save_budgets(budgets)
                    st.session_state["budgets"] = budgets
                    st.rerun()
    
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("### ➕ Add Budget")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        new_cat = st.selectbox("Category", DEFAULT_CATEGORIES, key="budget_cat")
    with col_b:
        new_limit = st.number_input("Monthly Limit", min_value=10.0, step=50.0, value=500.0)
    with col_c:
        st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)
        if st.button("Add Budget", use_container_width=True):
            budgets[new_cat] = float(new_limit)
            save_budgets(budgets)
            st.session_state["budgets"] = budgets
            st.rerun()

# ============================================================
# PAGE: GOALS
# ============================================================
elif page == "Goals":
    st.markdown("### 🎯 Goals")
    
    goals = st.session_state.get("goals", [])
    
    if not goals:
        st.info("No goals yet. Create your first one!")
    else:
        for idx, goal in enumerate(goals):
            pct = min(100, (goal["current"] / goal["target"] * 100)) if goal["target"] > 0 else 0
            
            col_goal, col_del = st.columns([4, 0.5])
            
            with col_goal:
                st.markdown(f"""
                <div class='card'>
                    <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>
                        <span style='font-weight: 700; color: #f1f5f9;'>{goal['name']}</span>
                        <span style='color: #94a3b8;'>${goal['current']:,.0f} / ${goal['target']:,.0f}</span>
                    </div>
                    <div class='progress-bar'><div class='progress-fill' style='width: {pct}%;'></div></div>
                    <div style='margin-top: 8px;'>
                        <span class='kpi-sub'>{pct:.0f}% complete</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_del:
                if st.button("❌", key=f"del_goal_{idx}", use_container_width=True):
                    goals.pop(idx)
                    save_goals(goals)
                    st.session_state["goals"] = goals
                    st.rerun()
    
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.markdown("### ➕ Create Goal")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        g_name = st.text_input("Goal Name", placeholder="e.g., Emergency Fund")
    with col_b:
        g_target = st.number_input("Target Amount", min_value=10.0, step=100.0, value=1000.0)
    with col_c:
        g_current = st.number_input("Current Amount", min_value=0.0, step=100.0, value=0.0)
    
    if st.button("Create Goal", use_container_width=True):
        if g_name.strip():
            new_goal = {"id": str(uuid.uuid4()), "name": g_name.strip(), "target": float(g_target), "current": float(g_current)}
            goals.append(new_goal)
            save_goals(goals)
            st.session_state["goals"] = goals
            st.rerun()

# ============================================================
# PAGE: SUBSCRIPTIONS
# ============================================================
elif page == "Subscriptions":
    st.markdown("### 📺 Subscriptions & Recurring")
    
    subs = detect_subscriptions(df_all)
    
    if subs:
        sub_total = sum([s["avg"] for s in subs])
        st.markdown(f"""
        <div class='info-box'>
            💰 <strong>${sub_total:,.0f}/month</strong> across <strong>{len(subs)}</strong> subscriptions
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<hr/>", unsafe_allow_html=True)
        
        for sub in subs:
            st.markdown(f"""
            <div class='card'>
                <div style='display: flex; justify-content: space-between;'>
                    <span style='color: #f1f5f9; font-weight: 700;'>{sub['merchant']}</span>
                    <span style='color: #94a3b8;'>${sub['avg']:,.0f}/mo • {sub['months']} months</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.markdown("<div class='success-box'>💡 Review recurring charges monthly to cut costs</div>", unsafe_allow_html=True)
    else:
        st.info("No recurring subscriptions detected yet")

# ============================================================
# PAGE: TRANSACTIONS
# ============================================================
elif page == "Transactions":
    st.markdown("### 🧾 All Transactions")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        type_f = st.selectbox("Type", ["All", "Income", "Expense", "Spending"], label_visibility="collapsed")
    with col_f2:
        cats = ["All"] + sorted(df_month["Category"].dropna().unique().tolist()) if not df_month.empty else ["All"]
        cat_f = st.selectbox("Category", cats, label_visibility="collapsed")
    with col_f3:
        min_f = st.number_input("Min $", value=0.0, step=10.0, label_visibility="collapsed")
    with col_f4:
        sort_f = st.selectbox("Sort", ["Newest", "Oldest", "High→Low", "Low→High"], label_visibility="collapsed")
    
    search_f = st.text_input("Search merchant/notes")
    
    st.markdown("<hr/>", unsafe_allow_html=True)
    
    filtered = df_month.copy()
    if not filtered.empty:
        if type_f != "All":
            filtered = filtered[filtered["Type"].str.lower() == type_f.lower()]
        if cat_f != "All":
            filtered = filtered[filtered["Category"] == cat_f]
        filtered = filtered[filtered["Amount"] >= float(min_f)]
        if search_f:
            s = search_f.lower()
            filtered = filtered[filtered["Merchant"].astype(str).str.lower().str.contains(s) | filtered["Notes"].astype(str).str.lower().str.contains(s)]
        
        if sort_f == "Newest":
            filtered = filtered.sort_values("Date", ascending=False)
        elif sort_f == "Oldest":
            filtered = filtered.sort_values("Date", ascending=True)
        elif sort_f == "High→Low":
            filtered = filtered.sort_values("Amount", ascending=False)
        else:
            filtered = filtered.sort_values("Amount", ascending=True)
    else:
        filtered = _empty_df()
    
    if filtered.empty:
        st.info("No transactions found")
    else:
        edited = st.data_editor(
            filtered[["Date", "Amount", "Type", "Category", "Merchant", "Notes"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date": st.column_config.DateColumn("Date"),
                "Amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                "Type": st.column_config.SelectboxColumn("Type", options=["Income", "Expense", "Spending"]),
                "Category": st.column_config.SelectboxColumn("Category", options=DEFAULT_CATEGORIES + INCOME_CATEGORIES),
            }
        )
        
        if st.button("💾 Save Changes", use_container_width=True):
            full = st.session_state["tx_df"].copy().set_index("ID")
            ids = filtered["ID"].tolist()
            edited2 = edited.copy()
            edited2["ID"] = ids
            edited2 = edited2.set_index("ID")
            
            for idx in edited2.index:
                full.loc[idx, ["Date","Amount","Type","Category","Merchant","Notes"]] = edited2.loc[idx, ["Date","Amount","Type","Category","Merchant","Notes"]]
            
            full = full.reset_index()
            full["Amount"] = pd.to_numeric(full["Amount"]).fillna(0.0)
            full["Date"] = pd.to_datetime(full["Date"]).dt.date
            
            save_transactions(full)
            st.session_state["tx_df"] = load_transactions()
            st.success("Saved! ✨")
            st.rerun()
