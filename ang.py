
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from pathlib import Path
import json
import uuid
import plotly.graph_objects as go
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

USERS_FILE = DATA_DIR / "users.json"

# User-specific data directories
def get_user_dir(username: str) -> Path:
    user_dir = DATA_DIR / username
    user_dir.mkdir(exist_ok=True)
    return user_dir

def get_tx_file(username: str) -> Path:
    return get_user_dir(username) / "transactions.json"

def get_budgets_file(username: str) -> Path:
    return get_user_dir(username) / "budgets.json"

def get_goals_file(username: str) -> Path:
    return get_user_dir(username) / "goals.json"

def get_theme_file(username: str) -> Path:
    return get_user_dir(username) / "theme.json"

SHEET_2025_TAB = "2025"
TX_TAB = "Transactions"

# Only this user syncs to Google Sheets (and can seed data from the 2025 sheet matrix)
SHEET_SYNC_USER = "ajoseph"  # Angela’s username (must match login username)

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
# BASE STYLES (theme overrides will be applied via apply_theme)
# ============================================================
st.markdown("""
<style>
* { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1600px;
}

.header-gradient {
    padding: 2.2rem 2.2rem;
    border-radius: 24px;
    margin-bottom: 1.5rem;
    box-shadow: 0 25px 50px rgba(236, 72, 153, 0.20);
    border: 1px solid rgba(236, 72, 153, 0.18);
}

.header-gradient h1 {
    margin: 0;
    font-size: 2.6rem;
}

.header-gradient p {
    margin: 0.55rem 0 0 0;
    font-size: 1.05rem;
}

.card {
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
    backdrop-filter: blur(10px);
    transition: all 0.25s ease;
}

.card:hover { transform: translateY(-2px); }

.kpi-label {
    opacity: 0.70;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    font-weight: 700;
    margin-bottom: 4px;
}

.kpi-value {
    font-size: 1.8rem;
    font-weight: 800;
    margin-bottom: 2px;
}

.kpi-sub {
    opacity: 0.70;
    font-size: 0.82rem;
}

.section-title {
    font-size: 1.25rem;
    font-weight: 800;
    margin-bottom: 12px;
}

.progress-bar {
    height: 6px;
    border-radius: 999px;
    overflow: hidden;
    margin-top: 8px;
}

.progress-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.25s ease;
}

.warning-box, .success-box, .info-box {
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 0.86rem;
}

hr {
    border: none;
    height: 1px;
    margin: 12px 0;
}

.stButton > button {
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 800 !important;
    font-size: 0.9rem !important;
}

[data-baseweb="input"] > div, [data-baseweb="select"] > div {
    border-radius: 8px !important;
}

[data-testid="stExpander"] {
    border-radius: 8px !important;
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

    # robust days-in-month
    days_in_month = (today.replace(day=28) + timedelta(days=4)).day
    day_of_month = today.day
    days_remaining = max(1, days_in_month - day_of_month)

    # remaining discretionary money
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

def get_ytd_metrics(df_all, year: int):
    df_ytd = df_all[df_all["Date"].apply(lambda d: isinstance(d, date) and d.year == year)]

    income = df_ytd[df_ytd["Type"].str.lower() == "income"]["Amount"].sum() if not df_ytd.empty else 0.0
    expenses = df_ytd[df_ytd["Type"].str.lower().isin(["expense", "spending"])]["Amount"].sum() if not df_ytd.empty else 0.0
    net = income - expenses
    savings_rate = ((income - expenses) / income * 100) if income > 0 else 0

    return {
        "income": income,
        "expenses": expenses,
        "net": net,
        "savings_rate": savings_rate,
        "tx_count": len(df_ytd),
    }

def detect_subscriptions(df_all):
    if df_all.empty:
        return []
    df_t = df_all.copy()
    df_t["YearMonth"] = df_t["Date"].apply(lambda d: month_key(d))
    merchants = df_t["Merchant"].unique()
    subs = []
    for merchant in merchants:
        if str(merchant).strip() == "" or merchant == "Budget 2025":
            continue
        m_data = df_t[df_t["Merchant"] == merchant]
        months_seen = m_data["YearMonth"].nunique()
        if months_seen >= 2:
            avg_amt = m_data["Amount"].mean()
            subs.append({"merchant": merchant, "months": months_seen, "avg": avg_amt})
    return sorted(subs, key=lambda x: x["months"], reverse=True)

# ============================================================
# USER MANAGEMENT (simple local users.json)
# ============================================================
def get_default_users() -> dict:
    return {
        "ajoseph": {"password": "ajoseph123", "role": "user"},
        "jjames": {"password": "Jaykayjay#99", "role": "admin"},
    }

def load_users() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text())
        except:
            return get_default_users()
    return get_default_users()

def save_users(users: dict) -> None:
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

if not USERS_FILE.exists():
    save_users(get_default_users())

# ============================================================
# THEME MANAGEMENT (per-user)
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
    if not st.session_state.get("authenticated", False):
        return DEFAULT_THEME.copy()
    theme_file = get_theme_file(st.session_state.username)
    if theme_file.exists():
        try:
            return json.loads(theme_file.read_text())
        except:
            return DEFAULT_THEME.copy()
    return DEFAULT_THEME.copy()

def save_theme(theme: dict) -> None:
    theme_file = get_theme_file(st.session_state.username)
    with open(theme_file, "w") as f:
        json.dump(theme, f, indent=2)

def apply_theme(theme: dict) -> None:
    bg_primary = theme.get("bg_primary", DEFAULT_THEME["bg_primary"])
    bg_secondary = theme.get("bg_secondary", DEFAULT_THEME["bg_secondary"])
    text_primary = theme.get("text_primary", DEFAULT_THEME["text_primary"])
    text_secondary = theme.get("text_secondary", DEFAULT_THEME["text_secondary"])
    accent = theme.get("accent", DEFAULT_THEME["accent"])
    accent_dark = theme.get("accent_dark", DEFAULT_THEME["accent_dark"])

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
        font-weight: 800;
        letter-spacing: -0.02em;
    }}

    .header-gradient {{
        background: linear-gradient(135deg, {accent} 0%, {accent_dark} 100%);
        border: 1px solid rgba(236, 72, 153, 0.2);
    }}

    .header-gradient h1 {{ color: white; }}
    .header-gradient p {{ color: rgba(255,255,255,0.85); }}

    .card {{
        border: 1px solid rgba(236, 72, 153, 0.18);
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.92) 0%, rgba(252, 231, 243, 0.82) 100%);
    }}

    .kpi-label {{ color: {text_secondary}; }}
    .kpi-value {{ color: {text_primary}; }}
    .kpi-sub {{ color: {text_secondary}; }}
    .section-title {{ color: {text_primary}; }}

    .progress-bar {{
        background: rgba(236, 72, 153, 0.10);
    }}
    .progress-fill {{
        background: linear-gradient(90deg, {accent}, {accent_dark});
    }}

    .warning-box {{
        background: rgba(239, 68, 68, 0.10);
        border: 1px solid rgba(239, 68, 68, 0.20);
        color: #991b1b;
    }}

    .success-box {{
        background: rgba(34, 197, 94, 0.10);
        border: 1px solid rgba(34, 197, 94, 0.20);
        color: #166534;
    }}

    .info-box {{
        background: rgba(236, 72, 153, 0.10);
        border: 1px solid rgba(236, 72, 153, 0.20);
        color: {text_primary};
    }}

    hr {{
        background: linear-gradient(90deg, transparent, rgba(236, 72, 153, 0.20), transparent);
    }}

    .stButton > button {{
        border: 1px solid rgba(236, 72, 153, 0.30) !important;
        background: linear-gradient(135deg, {accent} 0%, {accent_dark} 100%) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(236, 72, 153, 0.25) !important;
    }}

    .stButton > button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(236, 72, 153, 0.35) !important;
    }}

    [data-baseweb="input"] > div, [data-baseweb="select"] > div {{
        background-color: rgba(255, 255, 255, 0.90) !important;
        border-color: rgba(236, 72, 153, 0.15) !important;
    }}
    [data-baseweb="input"] input, [data-baseweb="select"] div {{
        color: {text_primary} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ============================================================
# DATA LAYER
# ============================================================
def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["ID", "Date", "Amount", "Type", "Category", "Merchant", "Notes"])

@st.cache_resource
def gs_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def parse_2025_tab(raw_data: list) -> pd.DataFrame:
    """
    Parses the budget matrix tab (2025) into pseudo-transactions ("Budget 2025" merchant),
    so the dashboard has baseline values even before manual transactions exist.
    """
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

        if category in INCOME_CATEGORIES or category == "INCOME":
            tx_type = "Income"
        elif category in SPENDING_CATEGORIES:
            tx_type = "Spending"
        else:
            tx_type = "Expense"

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

@st.cache_data(ttl=300)
def read_2025_budget_matrix() -> pd.DataFrame:
    gc = gs_client()
    sh = gc.open_by_key(st.secrets["GSHEET_ID"])
    ws = sh.worksheet(SHEET_2025_TAB)
    return parse_2025_tab(ws.get_all_values())

def write_transaction_to_sheet(row: dict):
    """
    Appends a row to the Transactions tab for audit trail.
    Adds username as last column.
    """
    gc = gs_client()
    sh = gc.open_by_key(st.secrets["GSHEET_ID"])
    ws = sh.worksheet(TX_TAB)
    ws.append_row([
        row["Date"],
        float(row["Amount"]),
        row["Type"],
        row["Category"],
        row.get("Merchant", ""),
        row.get("Notes", ""),
        st.session_state.username
    ])

def save_transactions(df: pd.DataFrame) -> None:
    tx_file = get_tx_file(st.session_state.username)
    out = df.copy()
    out["Date"] = out["Date"].astype(str)
    with open(tx_file, "w") as f:
        json.dump(out.to_dict(orient="records"), f, indent=2)

def load_transactions() -> pd.DataFrame:
    tx_file = get_tx_file(st.session_state.username)

    # 1) load local user file if it exists
    if tx_file.exists() and tx_file.stat().st_size > 0:
        try:
            data = json.loads(tx_file.read_text())
            df = pd.DataFrame(data)
            if not df.empty:
                df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
                df["Type"] = df.get("Type", "Expense").fillna("Expense")
                df["Category"] = df.get("Category", "Other").fillna("Other")
                df["Merchant"] = df.get("Merchant", "").fillna("")
                df["Notes"] = df.get("Notes", "").fillna("")
                # ensure ID exists
                if "ID" not in df.columns:
                    df["ID"] = [str(uuid.uuid4()) for _ in range(len(df))]
                return df[["ID","Date","Amount","Type","Category","Merchant","Notes"]]
        except:
            pass

    # 2) seed only Angela from Google Sheet matrix (optional baseline)
    if st.session_state.get("username") == SHEET_SYNC_USER:
        with st.spinner("✨ Seeding from Google Sheets (2025)…"):
            try:
                sheet_df = read_2025_budget_matrix()
                if sheet_df is not None and not sheet_df.empty:
                    sheet_df = sheet_df.copy()
                    sheet_df["ID"] = [str(uuid.uuid4()) for _ in range(len(sheet_df))]
                    sheet_df["Amount"] = pd.to_numeric(sheet_df["Amount"], errors="coerce").fillna(0.0)
                    sheet_df["Date"] = pd.to_datetime(sheet_df["Date"], errors="coerce").dt.date
                    sheet_df["Type"] = sheet_df.get("Type", "Expense").fillna("Expense")
                    sheet_df["Category"] = sheet_df.get("Category", "Other").fillna("Other")
                    sheet_df["Merchant"] = sheet_df.get("Merchant", "").fillna("")
                    sheet_df["Notes"] = sheet_df.get("Notes", "").fillna("")
                    save_transactions(sheet_df[["ID","Date","Amount","Type","Category","Merchant","Notes"]])
                    return sheet_df[["ID","Date","Amount","Type","Category","Merchant","Notes"]]
            except:
                pass

    return _empty_df()

def load_budgets() -> dict:
    budgets_file = get_budgets_file(st.session_state.username)
    if budgets_file.exists():
        try:
            return json.loads(budgets_file.read_text())
        except:
            return {}
    return {}

def save_budgets(budgets: dict) -> None:
    budgets_file = get_budgets_file(st.session_state.username)
    with open(budgets_file, "w") as f:
        json.dump(budgets, f, indent=2)

def load_goals() -> list:
    goals_file = get_goals_file(st.session_state.username)
    if goals_file.exists():
        try:
            return json.loads(goals_file.read_text())
        except:
            return []
    return []

def save_goals(goals: list) -> None:
    goals_file = get_goals_file(st.session_state.username)
    with open(goals_file, "w") as f:
        json.dump(goals, f, indent=2)

def add_transaction(df: pd.DataFrame, row: dict) -> pd.DataFrame:
    row["ID"] = row.get("ID") or str(uuid.uuid4())
    new_row = pd.DataFrame([row])
    new_row["Date"] = pd.to_datetime(new_row["Date"]).dt.date
    new_row["Amount"] = pd.to_numeric(new_row["Amount"]).fillna(0.0)
    df2 = pd.concat([df, new_row], ignore_index=True)

    save_transactions(df2)

    # only Angela syncs to google sheet
    if st.session_state.username == SHEET_SYNC_USER:
        try:
            write_transaction_to_sheet(row)
            st.toast("Synced ✨")
        except:
            st.toast("Saved locally ⚠️")
    else:
        st.toast("Saved ✨")

    return df2

# ============================================================
# LOGIN & MAIN APP
# ============================================================
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("username", None)
st.session_state.setdefault("role", "user")

if not st.session_state.authenticated:
    # LOGIN PAGE
    col_center = st.columns([1, 2, 1])[1]
    with col_center:
        st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='font-size: 3.2rem; color: #ec4899; margin-bottom: 0.5rem;'>💸 Money Hub</h1>
            <p style='font-size: 1.1rem; color: #be185d; margin-bottom: 2rem;'>Your Smart Budget Assistant</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

        with tab_login:
            st.markdown("### Welcome Back!")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", placeholder="Enter your password", type="password")

            if st.button("Login", use_container_width=True, key="login_btn"):
                users = load_users()
                if username in users and users[username]["password"] == password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.role = users[username].get("role", "user")
                    st.success("✨ Welcome back!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

        with tab_signup:
            st.markdown("### Create Your Account")
            new_username = st.text_input("Choose a username", placeholder="Enter a username", key="signup_user")
            new_password = st.text_input("Create a password", placeholder="Enter a password", type="password", key="signup_pass")
            new_password_confirm = st.text_input("Confirm password", placeholder="Confirm your password", type="password", key="signup_confirm")

            if st.button("Sign Up", use_container_width=True, key="signup_btn"):
                users = load_users()
                if new_username in users:
                    st.error("❌ Username already exists")
                elif new_password != new_password_confirm:
                    st.error("❌ Passwords don't match")
                elif len(new_password) < 4:
                    st.error("❌ Password must be at least 4 characters")
                elif new_username.strip() == "":
                    st.error("❌ Username cannot be empty")
                else:
                    users[new_username] = {"password": new_password, "role": "user"}
                    save_users(users)
                    st.success("✨ Account created! Please login.")

else:
    # MAIN APP
    st.session_state.setdefault("tx_df", load_transactions())
    st.session_state.setdefault("budgets", load_budgets())
    st.session_state.setdefault("goals", load_goals())
    st.session_state.setdefault("theme", load_theme())

    apply_theme(st.session_state["theme"])

    df_all = st.session_state["tx_df"].copy()
    today = date.today()

    months = sorted({month_key(d) for d in df_all["Date"].dropna().tolist() if pd.notna(d)})
    cur_m = month_key(today)
    if cur_m not in months:
        months.append(cur_m)
    months = sorted(months, reverse=True)

    years_available = sorted({d.year for d in df_all["Date"].dropna().tolist() if isinstance(d, date)})
    if today.year not in years_available:
        years_available.append(today.year)
    years_available = sorted(set(years_available), reverse=True)

    with st.sidebar:
        st.markdown("## 💸 Money Hub")
        st.markdown(f"<p style='color: #be185d;'><strong>Welcome, {st.session_state.username.title()}!</strong></p>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

        sel_month = st.selectbox("📅 Month", months, index=0, format_func=fmt_month)

        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

        page = st.radio(
            "Navigation",
            ["Home", "Dashboard", "Budgets", "Goals", "Subscriptions", "Transactions", "Year to Date"],
            label_visibility="collapsed"
        )

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
                bg_primary = st.color_picker("Primary BG", theme.get("bg_primary", DEFAULT_THEME["bg_primary"]), key="bg_primary")
                bg_secondary = st.color_picker("Secondary BG", theme.get("bg_secondary", DEFAULT_THEME["bg_secondary"]), key="bg_secondary")
            with col_b:
                st.markdown("**Text**")
                text_primary = st.color_picker("Primary Text", theme.get("text_primary", DEFAULT_THEME["text_primary"]), key="text_primary")
                text_secondary = st.color_picker("Secondary Text", theme.get("text_secondary", DEFAULT_THEME["text_secondary"]), key="text_secondary")

            st.markdown("**Accent**")
            col_c, col_d = st.columns(2)
            with col_c:
                accent = st.color_picker("Accent Color", theme.get("accent", DEFAULT_THEME["accent"]), key="accent")
            with col_d:
                accent_dark = st.color_picker("Accent Dark", theme.get("accent_dark", DEFAULT_THEME["accent_dark"]), key="accent_dark")

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
                st.success("Theme saved!")

        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.role = "user"
            st.rerun()

    # Month slice
    df_month = df_all[df_all["Date"].apply(lambda d: month_key(d) == sel_month if pd.notna(d) else False)].copy()
    if df_month.empty:
        df_month = _empty_df()

    metrics = get_month_metrics(df_month, df_all, sel_month, today)

    # ============================================================
    # PAGE: HOME
    # ============================================================
    if page == "Home":
        st.markdown(f"""
        <div class="header-gradient">
            <h1>Welcome, {st.session_state.username.title()}! 👋</h1>
            <p>Here's your financial overview at a glance</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"<div class='section-title'>📊 {fmt_month(sel_month)} Summary</div>", unsafe_allow_html=True)

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>💰 Income</div><div class='kpi-value'>${metrics['income']:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with k2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>💸 Expenses</div><div class='kpi-value'>${metrics['expenses']:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with k3:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>💚 Savings</div><div class='kpi-value'>${metrics['net']:,.0f}</div><div class='kpi-sub'>{metrics['savings_rate']:.0f}% saved</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with k4:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>🎯 Safe to Spend</div><div class='kpi-value'>${metrics['safe_to_spend']:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)

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

        t_merchant = st.text_input("Merchant", label_visibility="collapsed", key="add_merchant_home")
        t_notes = st.text_input("Notes", label_visibility="collapsed", key="add_notes_home")

        if st.button("💾 Save Transaction", use_container_width=True):
            if t_amt > 0:
                new = {"Date": str(t_date), "Amount": float(t_amt), "Type": t_type, "Category": t_cat, "Merchant": t_merchant, "Notes": t_notes}
                st.session_state["tx_df"] = add_transaction(st.session_state["tx_df"], new)
                st.rerun()

        st.markdown("<hr/>", unsafe_allow_html=True)

        st.markdown("### 💡 Quick Insights")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>Daily Budget</div><div class='kpi-value'>${metrics['daily_safe']:,.0f}</div><div class='kpi-sub'>{metrics['days_remaining']} days left</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col_b:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>Avg Transaction</div><div class='kpi-value'>${metrics['avg_tx']:,.0f}</div><div class='kpi-sub'>{len(df_month)} txns</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col_c:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>Spending Pace</div><div class='kpi-value'>${metrics['daily_spend']:,.0f}/day</div><div class='kpi-sub'>Projected: ${metrics['projected_month']:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # ============================================================
    # PAGE: DASHBOARD
    # ============================================================
    elif page == "Dashboard":
        st.markdown(f"<div class='section-title'>📊 {fmt_month(sel_month)}</div>", unsafe_allow_html=True)

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>💰 Income</div><div class='kpi-value'>${metrics['income']:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with k2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>💸 Expenses</div><div class='kpi-value'>${metrics['expenses']:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with k3:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>🎯 Safe to Spend</div><div class='kpi-value'>${metrics['safe_to_spend']:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with k4:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>📊 Net</div><div class='kpi-value'>${metrics['net']:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)

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

        if metrics["projected_month"] > metrics["income"]:
            st.markdown(f"<div class='warning-box'>⚠️ On pace to overspend by ${metrics['projected_month'] - metrics['income']:,.0f}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='success-box'>✓ You're in control!</div>", unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)

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
                fig.update_layout(
                    height=350,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=st.session_state["theme"].get("text_primary", "#be185d")),
                    margin=dict(l=80, r=0, t=0, b=0),
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No expenses this month")

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

    # ============================================================
    # PAGE: YEAR TO DATE
    # ============================================================
    elif page == "Year to Date":
        st.markdown("### 📈 Year to Date Overview")
        sel_year = st.selectbox("Year", years_available, index=0)

        ytd_metrics = get_ytd_metrics(df_all, sel_year)

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>💰 YTD Income</div><div class='kpi-value'>${ytd_metrics['income']:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with k2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>💸 YTD Expenses</div><div class='kpi-value'>${ytd_metrics['expenses']:,.0f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with k3:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>💚 YTD Net</div><div class='kpi-value'>${ytd_metrics['net']:,.0f}</div><div class='kpi-sub'>{ytd_metrics['savings_rate']:.0f}% saved</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with k4:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>📝 Transactions</div><div class='kpi-value'>{ytd_metrics['tx_count']}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr/>", unsafe_allow_html=True)

        st.markdown("### 📊 Monthly Breakdown")
        df_ytd = df_all[df_all["Date"].apply(lambda d: isinstance(d, date) and d.year == sel_year)]

        if not df_ytd.empty:
            df_ytd_copy = df_ytd.copy()
            df_ytd_copy["Month"] = df_ytd_copy["Date"].apply(lambda d: datetime(d.year, d.month, 1))

            inc_m = df_ytd_copy[df_ytd_copy["Type"].str.lower() == "income"].groupby("Month")["Amount"].sum()
            exp_m = df_ytd_copy[df_ytd_copy["Type"].str.lower().isin(["expense","spending"])].groupby("Month")["Amount"].sum()

            trend_df = pd.DataFrame({"Income": inc_m, "Expenses": exp_m}).fillna(0)
            trend_df["Net"] = trend_df["Income"] - trend_df["Expenses"]

            fig = go.Figure()
            fig.add_trace(go.Bar(x=trend_df.index, y=trend_df["Income"], name="Income"))
            fig.add_trace(go.Bar(x=trend_df.index, y=trend_df["Expenses"], name="Expenses"))
            fig.update_layout(
                height=400,
                barmode='group',
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=st.session_state["theme"].get("text_primary", "#be185d")),
                margin=dict(l=40, r=0, t=0, b=40),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No transactions for this year yet.")

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
                            <span style='font-weight: 800;'>{cat}</span>
                            <span style='opacity:0.75;'>${spent:,.0f} / ${limit:,.0f}</span>
                        </div>
                        <div class='progress-bar'><div class='progress-fill' style='width: {pct}%;'></div></div>
                        <div style='margin-top: 8px; display: flex; justify-content: space-between;'>
                            <span class='kpi-sub'>${remaining:,.0f} remaining ({100-pct:.0f}%)</span>
                    """, unsafe_allow_html=True)

                    if pct > metrics['expected_pct'] + 10:
                        st.markdown("<span style='color: #991b1b; font-size: 0.8rem;'>🚨 Too fast</span>", unsafe_allow_html=True)
                    elif pct < metrics['expected_pct'] - 10:
                        st.markdown("<span style='color: #166534; font-size: 0.8rem;'>✓ Ahead</span>", unsafe_allow_html=True)

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
                            <span style='font-weight: 800;'>{goal['name']}</span>
                            <span style='opacity:0.75;'>${goal['current']:,.0f} / ${goal['target']:,.0f}</span>
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
                        <span style='font-weight: 800;'>{sub['merchant']}</span>
                        <span style='opacity:0.75;'>${sub['avg']:,.0f}/mo • {sub['months']} months</span>
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
                filtered = filtered[
                    filtered["Merchant"].astype(str).str.lower().str.contains(s) |
                    filtered["Notes"].astype(str).str.lower().str.contains(s)
                ]

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
