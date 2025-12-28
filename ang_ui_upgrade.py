
import streamlit as st
import pandas as pd
from datetime import date, datetime
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
st.set_page_config(page_title="Money Hub 💸", page_icon="💸", layout="wide")

DATA_DIR = Path(".data")
DATA_DIR.mkdir(exist_ok=True)
TX_FILE = DATA_DIR / "transactions.json"

SHEET_2025_TAB = "2025"
TX_TAB = "Transactions"  # where manual adds are appended

DEFAULT_CATEGORIES = [
    "Rent", "Electricity", "Wifi", "Gas", "Phone Bill", "Student Loans",
    "Groceries", "Public Trans.", "Lyft/Ubers", "Subscriptions", "Eating Out",
    "Personal Stuff", "Credits", "Emergency Fund"
]

SPENDING_CATEGORIES = [
    "Groceries", "Public Trans.", "Lyft/Ubers", "Subscriptions",
    "Eating Out", "Personal Stuff", "Credits"
]

FIXED_EXPENSES = [
    "Rent", "Electricity", "Wifi", "Gas", "Phone Bill", "Student Loans",
    "Emergency Fund"
]

INCOME_CATEGORIES = ["Paycheck", "Other Income", "Gift", "Refund", "Bonus"]

CATEGORY_COLORS = {
    "Rent": "#ec4899", "Electricity": "#fbbf24", "Wifi": "#06b6d4", "Gas": "#f43f5e",
    "Phone Bill": "#f97316", "Student Loans": "#d946ef",
    "Groceries": "#10b981", "Public Trans.": "#a855f7", "Lyft/Ubers": "#8b5cf6",
    "Subscriptions": "#f97316", "Eating Out": "#fb7185", "Personal Stuff": "#f43f5e",
    "Credits": "#22c55e", "Emergency Fund": "#14b8a6",
    "Paycheck": "#10b981", "Other Income": "#34d399", "Gift": "#fbbf24",
    "Refund": "#06b6d4", "Bonus": "#f43f5e"
}

# ============================================================
# STYLES (inspired by your gs_readonly + modern cards/messages)
# ============================================================
st.markdown("""
<style>
* { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

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

.header-gradient {
    background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
    padding: 2rem;
    border-radius: 20px;
    margin-bottom: 1.2rem;
    box-shadow: 0 20px 60px rgba(236, 72, 153, 0.28);
}

.header-gradient h1 {
    color: white;
    margin: 0;
    font-size: 2.8rem;
}

.header-gradient p {
    color: rgba(255,255,255,0.85);
    margin: 0.5rem 0 0 0;
    font-size: 1rem;
}

.card {
    border: 1px solid rgba(244, 114, 182, 0.2);
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.92) 0%, rgba(254, 231, 243, 0.84) 100%);
    border-radius: 18px;
    padding: 16px 16px;
    box-shadow: 0 10px 28px rgba(236, 72, 153, 0.10);
    backdrop-filter: blur(10px);
    transition: all 0.25s ease;
}

.card:hover {
    transform: translateY(-2px);
    border-color: rgba(236, 72, 153, 0.45);
    box-shadow: 0 16px 38px rgba(236, 72, 153, 0.20);
}

.badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 0.82rem;
    border: 1px solid rgba(236, 72, 153, 0.22);
    background: rgba(236, 72, 153, 0.14);
    color: #be185d;
    margin-right: 6px;
    margin-bottom: 8px;
}

.kpi-label { 
    opacity: 0.72; 
    font-size: 0.85rem; 
    margin-bottom: 6px; 
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #be185d;
}
.kpi-value { 
    font-size: 1.95rem; 
    font-weight: 750; 
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

.small-muted { 
    opacity: 0.74; 
    font-size: 0.92rem; 
    color: #be185d;
}

hr { 
    border: none; 
    height: 1px; 
    background: linear-gradient(90deg, transparent, rgba(236, 72, 153, 0.20), transparent); 
    margin: 18px 0; 
}

[data-testid="stDataFrame"] { 
    border-radius: 16px; 
    overflow: hidden; 
    border: 1px solid rgba(236, 72, 153, 0.20); 
}

[data-testid="stExpander"] {
    border: 1px solid rgba(236, 72, 153, 0.20) !important;
    border-radius: 14px !important;
    background: rgba(255, 255, 255, 0.80) !important;
}

.stButton > button {
    border-radius: 14px !important;
    padding: 0.58rem 0.95rem !important;
    border: 1px solid rgba(236, 72, 153, 0.30) !important;
    background: linear-gradient(135deg, #ec4899 0%, #db2777 100%) !important;
    color: white !important;
    font-weight: 650 !important;
    box-shadow: 0 4px 15px rgba(236, 72, 153, 0.30) !important;
    transition: all 0.25s ease !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(236, 72, 153, 0.48) !important;
}

[data-baseweb="input"] > div, [data-baseweb="select"] > div {
    border-radius: 14px !important;
    background-color: rgba(255, 255, 255, 0.82) !important;
    border-color: rgba(236, 72, 153, 0.20) !important;
}
[data-baseweb="input"] input, [data-baseweb="select"] div {
    color: #831843 !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# GOOGLE SHEETS CLIENT
# ============================================================
@st.cache_resource
def gs_client():
    """Initialize Google Sheets client with service account."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    info = dict(st.secrets["gcp_service_account"])
    if "private_key" in info and isinstance(info["private_key"], str):
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=300)
def read_2025_budget_matrix() -> pd.DataFrame:
    """Read and parse the 2025 budget matrix tab (wide -> long tx rows)."""
    gc = gs_client()
    sheet_id = st.secrets["GSHEET_ID"]
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(SHEET_2025_TAB)
    raw = ws.get_all_values()
    return parse_2025_tab(raw)

def parse_2025_tab(raw_data: list) -> pd.DataFrame:
    """
    Parse your 2025 tab structure:
    - Month headers across columns (e.g., 'January 2025')
    - Categories in column index 2
    - Values are $ strings
    """
    if not raw_data or len(raw_data) < 2:
        return pd.DataFrame(columns=["Date", "Amount", "Type", "Category", "Merchant", "Notes"])

    # Find header row containing months
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

        # Your sheet: category is ALWAYS column 2
        category = str(row[2]).strip()

        # Skip summary/blank rows
        if not category or category in {"INCOME:", "SPENDING:", "EXPENSES:", "SAVINGS", "SAVINGS:", "TOTAL SAVED", "Bills", "Due"}:
            continue

        # Map to types
        if category == "INCOME":
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
                amount = float(amount_str.replace("$","").replace(",","").strip())
                month_date = datetime.strptime(month_str.strip(), "%B %Y")
                tx_date = month_date.replace(day=1).date()

                tx.append({
                    "Date": tx_date,
                    "Amount": amount,
                    "Type": tx_type,
                    "Category": category,
                    "Merchant": "Budget 2025",
                    "Notes": ""
                })
            except Exception:
                continue

    return pd.DataFrame(tx) if tx else pd.DataFrame(columns=["Date","Amount","Type","Category","Merchant","Notes"])

# ============================================================
# LOCAL CACHE + TX MERGE
# ============================================================
def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["ID", "Date", "Amount", "Type", "Category", "Merchant", "Notes"])

def save_transactions(df: pd.DataFrame) -> None:
    out = df.copy()
    out["Date"] = out["Date"].astype(str)
    with open(TX_FILE, "w") as f:
        json.dump(out.to_dict(orient="records"), f, indent=2)

def load_transactions() -> pd.DataFrame:
    """Load from local cache if present, else pull from sheet and cache."""
    if TX_FILE.exists() and TX_FILE.stat().st_size > 0:
        try:
            data = json.loads(TX_FILE.read_text())
            df = pd.DataFrame(data)
            if df.empty:
                return _empty_df()
            df["Amount"] = pd.to_numeric(df.get("Amount"), errors="coerce").fillna(0.0)
            df["Date"] = pd.to_datetime(df.get("Date"), errors="coerce").dt.date
            df["Type"] = df.get("Type", "Expense").fillna("Expense")
            df["Category"] = df.get("Category", "Other").fillna("Other")
            df["Merchant"] = df.get("Merchant", "").fillna("")
            df["Notes"] = df.get("Notes", "").fillna("")
            return df[["ID","Date","Amount","Type","Category","Merchant","Notes"]]
        except Exception:
            pass

    with st.spinner("✨ Pulling your real budget from Google Sheets…"):
        sheet_df = read_2025_budget_matrix()
        if sheet_df is None or sheet_df.empty:
            return _empty_df()
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

def write_to_sheet(df_new: pd.DataFrame) -> None:
    """Append new manual transactions to Transactions tab."""
    gc = gs_client()
    sh = gc.open_by_key(st.secrets["GSHEET_ID"])
    ws = sh.worksheet(TX_TAB)

    for _, r in df_new.iterrows():
        ws.append_row([
            str(r["Date"]),
            float(r["Amount"]),
            str(r["Type"]),
            str(r["Category"]),
            str(r["Merchant"]),
            str(r["Notes"]),
        ])

def add_transaction(df: pd.DataFrame, row: dict) -> pd.DataFrame:
    row = dict(row)
    row["ID"] = row.get("ID") or str(uuid.uuid4())
    new_row = pd.DataFrame([row])
    new_row["Date"] = pd.to_datetime(new_row["Date"], errors="coerce").dt.date
    new_row["Amount"] = pd.to_numeric(new_row["Amount"], errors="coerce").fillna(0.0)

    df2 = pd.concat([df, new_row], ignore_index=True)
    save_transactions(df2)

    # Best-effort sync
    try:
        write_to_sheet(new_row)
        st.toast("Synced to Google Sheets ✨", icon="✅")
    except Exception:
        st.toast("Saved locally (couldn't sync yet) ⚠️", icon="⚠️")

    return df2

def month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"

def fmt_month(k: str) -> str:
    return datetime.strptime(k + "-01", "%Y-%m-%d").strftime("%B %Y")

# ============================================================
# SESSION INIT
# ============================================================
st.session_state.setdefault("tx_df", load_transactions())
df_all = st.session_state["tx_df"].copy()

# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div class="header-gradient">
    <h1>💸 Money Hub</h1>
    <p>Real data from Google Sheets + cute insights ✨</p>
</div>
""", unsafe_allow_html=True)

top_left, top_right = st.columns([3.2, 1.2])

with top_left:
    st.markdown("<span class='badge'>✨ Sheet Connected</span>", unsafe_allow_html=True)
    st.markdown("<span class='badge'>📊 2025 Budget</span>", unsafe_allow_html=True)
    st.markdown("<span class='badge'>🧾 Manual adds → Transactions tab</span>", unsafe_allow_html=True)

with top_right:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    today = date.today()

    months = sorted({month_key(d) for d in df_all["Date"].dropna().tolist() if pd.notna(d)})
    cur_m = month_key(today)
    if cur_m not in months:
        months.append(cur_m)
    months = sorted(months, reverse=True)

    sel_month = st.selectbox("Month", months, index=0, format_func=fmt_month, label_visibility="collapsed")
    st.markdown("<div class='small-muted'>Choose a month to see the vibes</div>", unsafe_allow_html=True)

    cA, cB = st.columns([1, 1])
    with cA:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.session_state["tx_df"] = load_transactions()
            st.rerun()
    with cB:
        if st.button("🧹 Clear cache", use_container_width=True):
            try:
                if TX_FILE.exists():
                    TX_FILE.unlink()
            except Exception:
                pass
            st.cache_data.clear()
            st.session_state["tx_df"] = load_transactions()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# MONTH SLICE + KPIs
# ============================================================
df_month = df_all[df_all["Date"].apply(lambda d: month_key(d) == sel_month if pd.notna(d) else False)].copy()
if df_month.empty:
    df_month = _empty_df()

income = df_month[df_month["Type"].str.lower() == "income"]["Amount"].sum() if not df_month.empty else 0.0
expenses = df_month[df_month["Type"].str.lower().isin(["expense", "spending"])]["Amount"].sum() if not df_month.empty else 0.0
net = income - expenses

st.markdown("<hr/>", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

def kpi(col, label, value, sub=""):
    with col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-label'>{label}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-value'>{value}</div>", unsafe_allow_html=True)
        if sub:
            st.markdown(f"<div class='kpi-sub'>{sub}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

kpi(k1, "💰 Income", f"${income:,.2f}", "money in 💚")
kpi(k2, "💸 Expenses", f"${expenses:,.2f}", "money out 💸")
kpi(k3, "📊 Net", f"${net:,.2f}", "income − expenses")
kpi(k4, "📝 Entries", f"{len(df_month):,}", "this month")

# ============================================================
# QUICK ADD (cute, simple)
# ============================================================
st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

with st.expander("➕ Quick add (tap to open)", expanded=False):
    c1, c2, c3, c4 = st.columns([1.1, 1.0, 1.2, 2.0])
    with c1:
        t_date = st.date_input("Date", value=today, label_visibility="collapsed")
        t_type = st.selectbox("Type", ["Expense", "Spending", "Income"], label_visibility="collapsed")
    with c2:
        t_amount = st.number_input("Amount", min_value=0.0, step=5.0, format="%.2f", label_visibility="collapsed")
    with c3:
        if t_type == "Income":
            t_category = st.selectbox("Category", INCOME_CATEGORIES, label_visibility="collapsed")
        elif t_type == "Spending":
            t_category = st.selectbox("Category", SPENDING_CATEGORIES, label_visibility="collapsed")
        else:
            t_category = st.selectbox("Category", FIXED_EXPENSES, label_visibility="collapsed")
    with c4:
        t_merchant = st.text_input("Merchant", placeholder="e.g., Trader Joe’s", label_visibility="collapsed")
        t_notes = st.text_input("Notes", placeholder="optional ✨", label_visibility="collapsed")

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

# ============================================================
# FILTER BAR (inspired by gs_readonly)
# ============================================================
st.markdown("<div class='section-title'><h3>🔍 Filter & Search</h3></div>", unsafe_allow_html=True)

tool1, tool2, tool3, tool4, tool5 = st.columns([1.15, 1.3, 1.2, 1.7, 1.1])

with tool1:
    type_filter = st.selectbox("Show", ["All", "Income", "Expense", "Spending"], label_visibility="collapsed")
with tool2:
    cat_opts = ["All"] + sorted(df_month["Category"].dropna().unique().tolist()) if not df_month.empty else ["All"]
    cat_filter = st.selectbox("Category", cat_opts, label_visibility="collapsed")
with tool3:
    min_amt = st.number_input("Min $", value=0.0, step=10.0, label_visibility="collapsed")
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

    filtered = filtered[filtered["Amount"] >= float(min_amt)]

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
    filtered = _empty_df()

st.markdown("<hr/>", unsafe_allow_html=True)

# ============================================================
# MAIN: TRANSACTIONS + INSIGHTS
# ============================================================
left, right = st.columns([2.2, 1.0])

with left:
    st.markdown("<div class='section-title'><h3>🧾 Transactions</h3></div>", unsafe_allow_html=True)

    if filtered.empty:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.write("No transactions for this month.")
        st.markdown("<div class='small-muted'>Add one above or pick another month.</div>", unsafe_allow_html=True)
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
                    options=sorted(set(DEFAULT_CATEGORIES + INCOME_CATEGORIES))
                ),
            },
            key="editor_tx"
        )

        cA, cB = st.columns([1.2, 1.2])
        with cA:
            if st.button("Save edits 💾", use_container_width=True):
                full = st.session_state["tx_df"].copy().set_index("ID")

                ids = filtered["ID"].tolist()
                edited2 = edited.copy()
                edited2["ID"] = ids
                edited2 = edited2.set_index("ID")

                for idx in edited2.index:
                    full.loc[idx, ["Date","Amount","Type","Category","Merchant","Notes"]] = edited2.loc[idx, ["Date","Amount","Type","Category","Merchant","Notes"]]

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

    # Vibe card
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='kpi-label'>💫 This month’s vibe</div>", unsafe_allow_html=True)

    if expenses == 0 and income > 0:
        st.markdown("<div class='kpi-value'>Saving queen 👑</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-sub'>No expenses yet — love this for you.</div>", unsafe_allow_html=True)
    elif net >= 0:
        st.markdown("<div class='kpi-value'>Balanced ✨</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-sub'>You’re on top of it. Keep going.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='kpi-value'>Reset energy 🌙</div>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-sub'>A tiny tweak and you’re back.</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Top category + charts
    exp_only = df_month[df_month["Type"].str.lower().isin(["expense","spending"])].copy()
    if not exp_only.empty:
        by_cat = exp_only.groupby("Category")["Amount"].sum().sort_values(ascending=False)

        top_cat = by_cat.index[0]
        top_amt = float(by_cat.iloc[0])

        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='kpi-label'>🎯 Top spend</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-value'>{top_cat}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-sub'>${top_amt:,.2f}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Donut for share
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        fig_pie = go.Figure(
            data=[go.Pie(
                labels=by_cat.index,
                values=by_cat.values,
                hole=0.6,
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>$%{value:.2f}<extra></extra>",
            )]
        )
        fig_pie.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            height=320,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#831843")
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

# ============================================================
# TREND (across months) - lightweight analytics
# ============================================================
st.markdown("<hr/>", unsafe_allow_html=True)
st.markdown("<div class='section-title'><h3>📈 2025 Trend</h3></div>", unsafe_allow_html=True)

if not df_all.empty:
    df_all2 = df_all.copy()
    df_all2["Month"] = df_all2["Date"].apply(lambda d: datetime(d.year, d.month, 1))
    inc_m = df_all2[df_all2["Type"].str.lower() == "income"].groupby("Month")["Amount"].sum()
    exp_m = df_all2[df_all2["Type"].str.lower().isin(["expense","spending"])].groupby("Month")["Amount"].sum()
    trend = pd.DataFrame({"Income": inc_m, "Expenses": exp_m}).fillna(0.0)
    trend["Net"] = trend["Income"] - trend["Expenses"]
    trend = trend.sort_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trend.index, y=trend["Income"], mode="lines+markers", name="Income"))
    fig.add_trace(go.Scatter(x=trend.index, y=trend["Expenses"], mode="lines+markers", name="Expenses"))
    fig.add_trace(go.Scatter(x=trend.index, y=trend["Net"], mode="lines+markers", name="Net"))

    fig.update_layout(
        height=340,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#831843"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="",
        yaxis_title=""
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("No data yet — connect the sheet and refresh.")

# ============================================================
# FOOTER / SETTINGS
# ============================================================
with st.expander("⚙️ Data & Settings", expanded=False):
    st.markdown("**Sources**")
    st.write(f"- Read budget matrix from tab: `{SHEET_2025_TAB}`")
    st.write(f"- Append manual adds to tab: `{TX_TAB}`")
    st.markdown("<div class='small-muted'>Tip: if something looks off, click Refresh or Clear cache.</div>", unsafe_allow_html=True)
