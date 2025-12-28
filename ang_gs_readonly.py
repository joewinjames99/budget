import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from pathlib import Path
import json
import uuid
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
import warnings
import re
warnings.filterwarnings('ignore')

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Budget 💸", page_icon="💸", layout="wide")

DATA_DIR = Path(".data")
DATA_DIR.mkdir(exist_ok=True)
TX_FILE = DATA_DIR / "transactions.json"

DEFAULT_CATEGORIES = [
    "Rent", "Electricity", "Wifi", "Gas", "Phone Bill", "Student Loans",
    "Groceries", "Public Trans.", "Lyft/Ubers", "Subscriptions", "Eating Out", "Personal Stuff", "Credits", "Emergency Fund"
]

# Categorize expenses
SPENDING_CATEGORIES = [
    "Groceries", "Public Trans.", "Lyft/Ubers", "Subscriptions", "Eating Out", "Personal Stuff", "Credits"
]

FIXED_EXPENSES = [
    "Rent", "Electricity", "Wifi", "Gas", "Phone Bill", "Student Loans", "Emergency Fund"
]

INCOME_CATEGORIES = ["Paycheck", "Other Income", "Gift", "Refund", "Bonus"]

# Category colors for charts
CATEGORY_COLORS = {
    "Rent": "#ec4899", "Electricity": "#fbbf24", "Wifi": "#06b6d4", "Gas": "#f43f5e",
    "Phone Bill": "#f97316", "Student Loans": "#d946ef",
    "Groceries": "#10b981", "Public Trans.": "#ec4899", "Lyft/Ubers": "#ec4899",
    "Subscriptions": "#f97316", "Eating Out": "#f97316", "Personal Stuff": "#f43f5e",
    "Credits": "#10b981", "Emergency Fund": "#10b981",
    "Paycheck": "#10b981", "Other Income": "#34d399", "Gift": "#fbbf24", 
    "Refund": "#06b6d4", "Bonus": "#f43f5e"
}

# ----------------------------
# MODERN STYLES
# ----------------------------
st.markdown("""
<style>
.block-container { 
    padding-top: 1.2rem; 
    padding-bottom: 2.2rem; 
    max-width: 1400px; 
}

[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 50%, #fbcfe8 100%);
    color: #831843;
}

h1, h2, h3 { 
    letter-spacing: -0.02em; 
    color: #be185d;
}

.card {
    border: 1px solid rgba(244, 114, 182, 0.2);
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(254, 231, 243, 0.8) 100%);
    border-radius: 18px;
    padding: 16px 16px;
    box-shadow: 0 10px 28px rgba(236, 72, 153, 0.1);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.card:hover {
    transform: translateY(-2px);
    border-color: rgba(236, 72, 153, 0.5);
    box-shadow: 0 15px 35px rgba(236, 72, 153, 0.25);
}

.badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 0.82rem;
    border: 1px solid rgba(236, 72, 153, 0.2);
    background: rgba(236, 72, 153, 0.15);
    color: #be185d;
    margin-right: 6px;
    margin-bottom: 8px;
}

.kpi-label { 
    opacity: 0.72; 
    font-size: 0.9rem; 
    margin-bottom: 6px; 
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #be185d;
}
.kpi-value { 
    font-size: 1.95rem; 
    font-weight: 700; 
    letter-spacing: -0.02em;
    color: #831843;
}
.kpi-sub { 
    opacity: 0.72; 
    font-size: 0.85rem; 
    margin-top: 4px;
    color: #be185d;
}

.section-title {
    display: flex; 
    align-items: center; 
    justify-content: space-between;
    margin-top: 4px; 
    margin-bottom: 10px;
}
.section-title h3 { 
    margin: 0; 
    padding: 0; 
    color: #be185d;
    font-size: 1.4rem;
}

hr { 
    border: none; 
    height: 1px; 
    background: linear-gradient(90deg, transparent, rgba(236, 72, 153, 0.2), transparent); 
    margin: 18px 0; 
}

[data-testid="stDataFrame"] { 
    border-radius: 16px; 
    overflow: hidden; 
    border: 1px solid rgba(236, 72, 153, 0.2); 
}

.stButton > button {
    border-radius: 14px !important;
    padding: 0.58rem 0.95rem !important;
    border: 1px solid rgba(236, 72, 153, 0.3) !important;
    background: linear-gradient(135deg, #ec4899 0%, #db2777 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 15px rgba(236, 72, 153, 0.3) !important;
    transition: all 0.3s ease !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(236, 72, 153, 0.5) !important;
}

[data-baseweb="input"] > div, [data-baseweb="select"] > div {
    border-radius: 14px !important;
    background-color: rgba(255, 255, 255, 0.8) !important;
    border-color: rgba(236, 72, 153, 0.2) !important;
}

[data-baseweb="input"] input, [data-baseweb="select"] div {
    color: #831843 !important;
}

.small-muted { 
    opacity: 0.72; 
    font-size: 0.92rem; 
    color: #be185d;
}

[data-testid="stExpander"] {
    border: 1px solid rgba(236, 72, 153, 0.2) !important;
    border-radius: 14px !important;
    background: rgba(255, 255, 255, 0.8) !important;
}

.header-gradient {
    background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
    padding: 2rem;
    border-radius: 20px;
    margin-bottom: 1.5rem;
    box-shadow: 0 20px 60px rgba(236, 72, 153, 0.3);
}

.header-gradient h1 {
    color: white;
    margin: 0;
    font-size: 2.8rem;
}

.header-gradient p {
    color: rgba(255,255,255,0.85);
    margin: 0.5rem 0 0 0;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# GOOGLE SHEETS CLIENT
# ----------------------------
@st.cache_resource
def gs_client():
    """Initialize Google Sheets client with service account"""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        info = dict(st.secrets["gcp_service_account"])
        
        # Normalize private key if needed
        if "private_key" in info and isinstance(info["private_key"], str):
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Failed to authenticate with Google Sheets: {e}")
        return None

@st.cache_data(ttl=300)
def read_sheet_data():
    """Read transactions from Google Sheet 2025 tab and parse"""
    try:
        gc = gs_client()
        if gc is None:
            return None
        
        sheet_id = st.secrets["GSHEET_ID"]
        
        sh = gc.open_by_key(sheet_id)
        ws = sh.worksheet("2025")  # Read from 2025 tab
        data = ws.get_all_values()
        
        if not data:
            st.warning("No data found in '2025' tab")
            return None
        
        return parse_2025_tab(data)
    except Exception as e:
        st.error(f"❌ Error reading sheet: {e}")
        return None
def parse_budget_matrix(df_raw):
    # First row contains month headers
    months = df_raw.columns[1:]

    records = []

    for _, row in df_raw.iterrows():
        category = str(row.iloc[0]).strip()

        # Skip empty rows
        if not category or category.upper() in ["", "NAN"]:
            continue

        # Determine type
        is_income = category.upper() == "INCOME"
        row_type = "Income" if is_income else "Expense"

        for month in months:
            val = row[month]

            if pd.isna(val):
                continue

            # Clean $ and commas
            amt = (
                str(val)
                .replace("$", "")
                .replace(",", "")
                .replace("(", "-")
                .replace(")", "")
                .strip()
            )

            try:
                amt = float(amt)
            except ValueError:
                continue

            records.append({
                "Month": pd.to_datetime(month),
                "Category": category,
                "Amount": amt,
                "Type": row_type,
            })

    return pd.DataFrame(records)
def parse_2025_tab(raw_data: list) -> pd.DataFrame:
    """Parse 2025 tab format into transactions (budget matrix -> long rows)."""
    if not raw_data or len(raw_data) < 2:
        st.error("No data in 2025 tab")
        return None

    transactions = []

    # Debug
    st.write("🔍 **Debug Info:**")
    st.write(f"Total rows: {len(raw_data)}")
    st.write(f"First row: {raw_data[0][:8]}")

    # Find the header row (contains month names like "January 2025")
    header_row_idx = None
    for i, row in enumerate(raw_data):
        if any("2025" in str(cell) for cell in row):
            header_row_idx = i
            st.write(f"Found header at row {i}")
            break

    if header_row_idx is None:
        st.error("❌ Could not find header row with '2025'")
        return None

    header_row = raw_data[header_row_idx]
    st.write(f"Header: {header_row[:12]}")

    # Extract ALL month columns (any cell that has a month name AND 2025)
    months = []
    month_cols = []

    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    for col_idx, cell in enumerate(header_row):
        cell_str = str(cell).strip()
        if ("2025" in cell_str) and any(m in cell_str for m in month_names):
            months.append(cell_str)
            month_cols.append(col_idx)

    st.write(f"Found {len(months)} months: {months}")
    st.write(f"Month columns: {month_cols}")

    if not months:
        st.error("❌ No months found in header row")
        return None

    # Parse each category row
    for row_idx in range(header_row_idx + 1, len(raw_data)):
        row = raw_data[row_idx]

        if not row or len(row) <= 2:
            continue

        # ✅ IMPORTANT: category is ALWAYS column 2 for your sheet
        category = str(row[2]).strip()

        # Skip summary + empty rows
        if not category or category in [
            "INCOME:", "SPENDING:", "EXPENSES:", "SAVINGS", "SAVINGS:", "TOTAL SAVED",
            "", "Bills", "Due"
        ]:
            continue

        # Determine type (keep your existing mappings)
        if category == "INCOME":
            tx_type = "Income"
        elif category in SPENDING_CATEGORIES:
            tx_type = "Spending"
        elif category in FIXED_EXPENSES:
            tx_type = "Expense"
        else:
            tx_type = "Expense"

        # Extract amounts for each month
        for month_str, col_idx in zip(months, month_cols):
            if col_idx >= len(row):
                continue

            amount_str = str(row[col_idx]).strip()
            if not amount_str:
                continue

            try:
                # Parse amount ($ and commas)
                amount = float(amount_str.replace("$", "").replace(",", ""))

                # ✅ IMPORTANT: DO NOT skip zeros (zero months should still exist)
                # if amount == 0:
                #     continue

                # Parse month/year - handle both "January 2025" and "Jan 2025"
                month_str_clean = month_str.strip()

                # Most likely it's already "January 2025", but keep the fallback
                try:
                    month_date = datetime.strptime(month_str_clean, "%B %Y")
                except:
                    month_date = datetime.strptime(month_str_clean, "%b %Y")

                tx_date = month_date.replace(day=1).date()

                transactions.append({
                    "Date": tx_date,
                    "Amount": amount,
                    "Type": tx_type,
                    "Category": category,
                    "Merchant": "Budget 2025",
                    "Notes": ""
                })

            except Exception as e:
                st.write(f"Error parsing {category} {month_str}: {e}")
                continue

    st.write(f"✅ Parsed {len(transactions)} transactions")
    return pd.DataFrame(transactions) if transactions else None

# ----------------------------
# DATA LAYER
# ----------------------------
def load_transactions() -> pd.DataFrame:
    """Load transactions from Google Sheet or local cache"""
    # Try local cache first
    if TX_FILE.exists() and TX_FILE.stat().st_size > 0:
        try:
            with open(TX_FILE) as f:
                data = json.load(f)
            df = pd.DataFrame(data)
            if not df.empty:
                df["Amount"] = pd.to_numeric(df.get("Amount"), errors="coerce").fillna(0.0)
                df["Date"] = pd.to_datetime(df.get("Date"), errors="coerce").dt.date
                df["Type"] = df.get("Type", "Expense").fillna("Expense")
                df["Category"] = df.get("Category", "Other").fillna("Other")
                df["Merchant"] = df.get("Merchant", "").fillna("")
                df["Notes"] = df.get("Notes", "").fillna("")
                return df[["ID", "Date", "Amount", "Type", "Category", "Merchant", "Notes"]]
        except Exception as e:
            st.warning(f"Cache error: {e}")
    
    # Fetch from Google Sheet
    with st.spinner("📊 Loading from 2025 tab..."):
        sheet_df = read_sheet_data()
        
        if sheet_df is not None and not sheet_df.empty:
            # Add IDs
            sheet_df["ID"] = [str(uuid.uuid4()) for _ in range(len(sheet_df))]
            
            # Ensure proper types
            sheet_df["Amount"] = pd.to_numeric(sheet_df["Amount"], errors="coerce").fillna(0.0)
            sheet_df["Date"] = pd.to_datetime(sheet_df["Date"], errors="coerce").dt.date
            sheet_df["Type"] = sheet_df.get("Type", "Expense").fillna("Expense")
            sheet_df["Category"] = sheet_df.get("Category", "Other").fillna("Other")
            sheet_df["Merchant"] = sheet_df.get("Merchant", "").fillna("")
            sheet_df["Notes"] = sheet_df.get("Notes", "").fillna("")
            
            save_transactions(sheet_df[["ID", "Date", "Amount", "Type", "Category", "Merchant", "Notes"]])
            st.success("✨ Data loaded from 2025 tab!")
            return sheet_df[["ID", "Date", "Amount", "Type", "Category", "Merchant", "Notes"]]
    
    # Fallback
    return pd.DataFrame(columns=["ID", "Date", "Amount", "Type", "Category", "Merchant", "Notes"])

def save_transactions(df: pd.DataFrame) -> None:
    """Save transactions to local JSON"""
    out = df.copy()
    out["Date"] = out["Date"].astype(str)
    with open(TX_FILE, 'w') as f:
        json.dump(out.to_dict(orient="records"), f, indent=2)

def add_transaction(df: pd.DataFrame, row: dict) -> pd.DataFrame:
    """Add new transaction"""
    row = dict(row)
    row["ID"] = row.get("ID") or str(uuid.uuid4())
    new_row = pd.DataFrame([row])
    new_row["Date"] = pd.to_datetime(new_row["Date"]).dt.date
    new_row["Amount"] = pd.to_numeric(new_row["Amount"], errors="coerce").fillna(0.0)
    df2 = pd.concat([df, new_row], ignore_index=True)
    save_transactions(df2)
    
    # Write to Google Sheet
    try:
        write_to_sheet(new_row)
    except Exception as e:
        st.warning(f"⚠️ Saved locally but couldn't sync to sheet: {e}")
    
    return df2

def write_to_sheet(df: pd.DataFrame) -> None:
    """Write new transactions to Transactions tab"""
    gc = gs_client()
    if gc is None:
        return
    
    try:
        sheet_id = st.secrets["GSHEET_ID"]
        
        sh = gc.open_by_key(sheet_id)
        ws = sh.worksheet("Transactions")  # Write to Transactions tab
        
        # Convert dataframe to list of lists
        for _, row in df.iterrows():
            values = [
                str(row["Date"]),
                float(row["Amount"]),
                str(row["Type"]),
                str(row["Category"]),
                str(row["Merchant"]),
                str(row["Notes"])
            ]
            ws.append_row(values)
        
        st.success("✨ Synced to Transactions tab!")
    except Exception as e:
        st.error(f"Error writing to sheet: {e}")

def month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"

def fmt_month(k: str) -> str:
    return datetime.strptime(k + "-01", "%Y-%m-%d").strftime("%B %Y")

# ----------------------------
# SESSION INIT
# ----------------------------
st.session_state.setdefault("tx_df", load_transactions())
df_all = st.session_state["tx_df"].copy()

# ----------------------------
# HEADER
# ----------------------------
st.markdown("""
<div class="header-gradient">
    <h1>💸 Money Hub</h1>
    <p>Your finances synced from Google Sheets</p>
</div>
""", unsafe_allow_html=True)

top_left, top_right = st.columns([3.2, 1.2])

with top_left:
    col1, col2, col3 = st.columns([1, 1, 1.5])
    with col1:
        st.markdown("<span class='badge'>✨ Sheet Connected</span>", unsafe_allow_html=True)
    with col2:
        st.markdown("<span class='badge'>📊 Real Data</span>", unsafe_allow_html=True)
    with col3:
        if st.button("🔄 Refresh", key="refresh_header"):
            st.cache_data.clear()
            st.session_state["tx_df"] = load_transactions()
            st.rerun()

with top_right:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    today = date.today()
    months = sorted({month_key(d) for d in df_all["Date"].dropna().tolist() if pd.notna(d)})
    cur_m = month_key(today)
    if cur_m not in months:
        months.append(cur_m)
    months = sorted(months, reverse=True)

    sel_month = st.selectbox("Month", months, index=0, format_func=fmt_month, label_visibility="collapsed")
    st.markdown("<div class='small-muted'>Connected to Transactions tab</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Month slice
df = df_all.copy()
df_month = df[df["Date"].apply(lambda d: month_key(d) == sel_month if pd.notna(d) else False)].copy()

if df_month.empty:
    df_month = pd.DataFrame(columns=["ID", "Date", "Amount", "Type", "Category", "Merchant", "Notes"])

income = df_month[df_month["Type"].str.lower() == "income"]["Amount"].sum() if not df_month.empty else 0.0
expenses = df_month[(df_month["Type"].str.lower() == "expense") | (df_month["Type"].str.lower() == "spending")]["Amount"].sum() if not df_month.empty else 0.0
net = income - expenses

st.markdown("<hr/>", unsafe_allow_html=True)

# ----------------------------
# KPI CARDS
# ----------------------------
k1, k2, k3, k4 = st.columns(4)

def kpi_card(col, label, value, sub="", icon=""):
    with col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>{icon} {label}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-value'>{value}</div>", unsafe_allow_html=True)
        if sub:
            st.markdown(f"<div class='kpi-sub'>{sub}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

kpi_card(k1, "Income", f"${income:,.2f}", "money in 💚", "💰")
kpi_card(k2, "Expenses", f"${expenses:,.2f}", "money out 💸", "💸")
kpi_card(k3, "Net", f"${net:,.2f}", "income − expenses", "📊")
kpi_card(k4, "Transactions", f"{len(df_month):,}", "this month", "📝")

st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

# ----------------------------
# QUICK ADD
# ----------------------------
with st.expander("➕ Quick add transaction (tap to open)", expanded=False):
    c1, c2, c3, c4 = st.columns([1.1, 1, 1.1, 1.8])

    with c1:
        t_date = st.date_input("Date", value=today, label_visibility="collapsed")
        t_type = st.radio("Type", ["Expense", "Income", "Savings"], horizontal=True, label_visibility="collapsed")

    with c2:
        t_amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f", label_visibility="collapsed")

    with c3:
        if t_type == "Expense":
            t_category = st.selectbox("Category", FIXED_EXPENSES, label_visibility="collapsed")
        elif t_type == "Spending":
            t_category = st.selectbox("Category", SPENDING_CATEGORIES, label_visibility="collapsed")
        elif t_type == "Income":
            t_category = st.selectbox("Category", INCOME_CATEGORIES, label_visibility="collapsed")
        else:
            t_category = st.selectbox("Category", DEFAULT_CATEGORIES, label_visibility="collapsed")

    with c4:
        t_merchant = st.text_input("Merchant", placeholder="e.g., Trader Joe's", label_visibility="collapsed")
        t_notes = st.text_input("Notes", placeholder="optional", label_visibility="collapsed")

    b1, b2 = st.columns([1.2, 1.2])
    with b1:
        if st.button("Save ✅", use_container_width=True):
            if t_amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                new = {
                    "Date": str(t_date),
                    "Amount": float(t_amount),
                    "Type": t_type,
                    "Category": t_category,
                    "Merchant": t_merchant.strip(),
                    "Notes": t_notes.strip(),
                }
                st.session_state["tx_df"] = add_transaction(st.session_state["tx_df"], new)
                st.success("Saved ✨")
                st.rerun()

st.markdown("<hr/>", unsafe_allow_html=True)

# ----------------------------
# FILTERS & SEARCH
# ----------------------------
st.markdown("<div class='section-title'><h3>🔍 Filter & Search</h3></div>", unsafe_allow_html=True)

tool1, tool2, tool3, tool4, tool5 = st.columns([1.15, 1.3, 1.2, 1.6, 1.1])

with tool1:
    type_filter = st.selectbox("Show", ["All", "Income", "Expense", "Spending"], label_visibility="collapsed")
with tool2:
    cat_opts = ["All"] + sorted(df_month["Category"].dropna().unique().tolist()) if not df_month.empty else ["All"]
    cat_filter = st.selectbox("Category", cat_opts, label_visibility="collapsed")
with tool3:
    min_amt = st.number_input("Min $", value=0.0, step=5.0, label_visibility="collapsed")
with tool4:
    q = st.text_input("Search", placeholder="merchant or notes…", label_visibility="collapsed")
with tool5:
    sort_mode = st.selectbox("Sort", ["Newest", "Oldest", "Highest $", "Lowest $"], label_visibility="collapsed")

filtered = df_month.copy()

if not filtered.empty:
    filtered["Amount"] = pd.to_numeric(filtered["Amount"], errors="coerce").fillna(0.0)

    if type_filter != "All":
        filtered = filtered[filtered["Type"].str.lower() == type_filter.lower()]

    if cat_filter != "All":
        filtered = filtered[filtered["Category"] == cat_filter]

    filtered = filtered[filtered["Amount"] >= min_amt]

    if q:
        s = q.lower().strip()
        filtered = filtered[
            filtered["Merchant"].astype(str).str.lower().str.contains(s) |
            filtered["Notes"].astype(str).str.lower().str.contains(s)
        ]

    if sort_mode == "Newest":
        filtered = filtered.sort_values("Date", ascending=False)
    elif sort_mode == "Oldest":
        filtered = filtered.sort_values("Date", ascending=True)
    elif sort_mode == "Highest $":
        filtered = filtered.sort_values("Amount", ascending=False)
    else:
        filtered = filtered.sort_values("Amount", ascending=True)
else:
    filtered = pd.DataFrame(columns=["ID", "Date", "Amount", "Type", "Category", "Merchant", "Notes"])

st.markdown("<hr/>", unsafe_allow_html=True)

# ----------------------------
# MAIN LAYOUT: TRANSACTIONS + INSIGHTS
# ----------------------------
left, right = st.columns([2.2, 1])

with left:
    st.markdown("<div class='section-title'><h3>🧾 Transactions</h3></div>", unsafe_allow_html=True)

    if filtered.empty:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write("No transactions for this month.")
        st.markdown("<div class='small-muted'>Add a new transaction or select a different month.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        view = filtered.copy()

        edited = st.data_editor(
            view,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_order=["Date", "Amount", "Type", "Category", "Merchant", "Notes"],
            column_config={
                "Date": st.column_config.DateColumn("Date"),
                "Amount": st.column_config.NumberColumn("Amount", format="%.2f"),
                "Type": st.column_config.SelectboxColumn("Type", options=["Income", "Expense", "Spending"]),
                "Category": st.column_config.SelectboxColumn(
                    "Category",
                    options=DEFAULT_CATEGORIES + INCOME_CATEGORIES
                ),
            },
            key="editor_tx"
        )

        cA, cB = st.columns([1.2, 1.2])

        with cA:
            if st.button("Save edits 💾", use_container_width=True):
                full = st.session_state["tx_df"].copy()
                full = full.set_index("ID")

                ids = filtered["ID"].tolist()
                edited2 = edited.copy()
                edited2["ID"] = ids
                edited2 = edited2.set_index("ID")

                for idx in edited2.index:
                    full.loc[idx, ["Date", "Amount", "Type", "Category", "Merchant", "Notes"]] = edited2.loc[idx, ["Date", "Amount", "Type", "Category", "Merchant", "Notes"]]

                full = full.reset_index()
                full["Amount"] = pd.to_numeric(full["Amount"], errors="coerce").fillna(0.0)
                full["Date"] = pd.to_datetime(full["Date"], errors="coerce").dt.date

                save_transactions(full)
                st.session_state["tx_df"] = load_transactions()
                st.success("Saved ✨")
                st.rerun()

        with cB:
            if st.button("Delete month 🗑️", use_container_width=True):
                full = st.session_state["tx_df"].copy()
                full = full[~full["Date"].apply(lambda d: month_key(d) == sel_month if pd.notna(d) else False)]
                save_transactions(full)
                st.session_state["tx_df"] = load_transactions()
                st.success("Deleted this month ✨")
                st.rerun()

with right:
    st.markdown("<div class='section-title'><h3>✨ Insights</h3></div>", unsafe_allow_html=True)

    if df_month.empty:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write("Add transactions to unlock insights.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        exp_only = df_month[df_month["Type"].str.lower() == "expense"].copy()

        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-label'>💫 This month's vibe</div>", unsafe_allow_html=True)

        if expenses == 0 and income > 0:
            st.markdown("<div class='kpi-value'>Saving queen 👑</div>", unsafe_allow_html=True)
            st.markdown("<div class='kpi-sub'>No expenses yet!</div>", unsafe_allow_html=True)
        elif expenses > 0 and net >= 0:
            st.markdown("<div class='kpi-value'>Balanced ✨</div>", unsafe_allow_html=True)
            st.markdown("<div class='kpi-sub'>You're on top of it.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='kpi-value'>Time to reset 🌙</div>", unsafe_allow_html=True)
            st.markdown("<div class='kpi-sub'>Let's make a plan.</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        if not exp_only.empty:
            by_cat = exp_only.groupby("Category")["Amount"].sum().sort_values(ascending=False)
            top_cat = by_cat.index[0]
            top_amt = float(by_cat.iloc[0])

            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>🎯 Top spend</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-value'>{top_cat}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-sub'>${top_amt:,.2f}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            st.markdown("<h4 style='color: #be185d; margin-bottom: 12px;'>💹 Spend by category</h4>", unsafe_allow_html=True)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=by_cat.index,
                y=by_cat.values,
                marker_color=[CATEGORY_COLORS.get(cat, "#95A5A6") for cat in by_cat.index],
                text=[f"${v:.2f}" for v in by_cat.values],
                textposition="auto",
                hovertemplate="<b>%{x}</b><br>$%{y:.2f}<extra></extra>"
            ))
            fig.update_layout(
                title="",
                xaxis_title="",
                yaxis_title="",
                hovermode="x unified",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#831843"),
                margin=dict(l=0, r=0, t=0, b=40),
                height=300
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            st.markdown("<h4 style='color: #be185d; margin-bottom: 12px;'>💡 Suggestions</h4>", unsafe_allow_html=True)
            st.markdown(f"""
            - Your highest spend is **{top_cat}** at **${top_amt:,.2f}**
            - Try setting a monthly budget for each category
            - Track your progress month over month
            """)

st.markdown("<hr/>", unsafe_allow_html=True)

# ----------------------------
# FOOTER
# ----------------------------
with st.expander("📊 Data Source & Settings", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Google Sheet Integration:**
        - Reading from: Transactions tab
        - Auto-syncs every 5 minutes
        - Cached locally for fast access
        """)
    with col2:
        if st.button("Clear Cache & Reload", use_container_width=True):
            st.cache_data.clear()
            st.session_state["tx_df"] = load_transactions()
            st.rerun()