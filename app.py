import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import bcrypt
from datetime import datetime

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="KWR Plot Map",
    layout="wide"
)

# ---------------- CSS ----------------
st.markdown("""
<style>
.plot-grid {display:grid;grid-template-columns:repeat(auto-fill,minmax(70px,1fr));gap:10px}
.plot {padding:15px;border-radius:8px;color:white;font-weight:bold;text-align:center}
.Available{background:#28a745}
.Booked{background:#ffc107;color:black}
.Sold{background:#dc3545}
.footer{text-align:center;color:#777;margin-top:30px}
</style>
""", unsafe_allow_html=True)

# ---------------- DB CONNECTION ----------------
@st.cache_resource
def get_engine():
    db = st.secrets["mysql"]
    uri = (
        f"mysql+pymysql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{db['database']}"
    )
    return create_engine(
        uri,
        pool_pre_ping=True,
        pool_recycle=280,
        connect_args={"connect_timeout": 10}
    )

def query_df(sql, params=None):
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)

def exec_query(sql, params=None):
    with get_engine().begin() as conn:
        conn.execute(text(sql), params or {})

# ---------------- AUTH ----------------
def hash_pw(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def check_pw(pw, hashed):
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def login(phone, password):
    q = "SELECT name,password_hash,is_admin FROM users WHERE phone_number=:p"
    row = query_df(q, {"p": phone})
    if row.empty:
        return False
    if check_pw(password, row.iloc[0]["password_hash"]):
        st.session_state.user = row.iloc[0]["name"]
        st.session_state.phone = phone
        st.session_state.admin = bool(row.iloc[0]["is_admin"])
        exec_query("UPDATE users SET last_seen=NOW() WHERE phone_number=:p", {"p": phone})
        return True
    return False

# ---------------- SESSION INIT ----------------
if "phone" not in st.session_state:
    st.session_state.phone = None
    st.session_state.admin = False

# ---------------- LOGIN PAGE ----------------
if not st.session_state.phone:
    st.title("🔐 Login")

    with st.form("login"):
        phone = st.text_input("Phone")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if login(phone, password):
                st.rerun()
            else:
                st.error("Invalid credentials")

    st.markdown('<div class="footer">Built by <a href="https://aiclex.in">AICLEX TECHNOLOGIES</a></div>', unsafe_allow_html=True)
    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.success(f"Logged in: {st.session_state.user}")
if st.session_state.admin:
    st.sidebar.warning("Admin Access")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# ---------------- PROJECT SELECT ----------------
projects = query_df("SELECT id,name FROM projects ORDER BY name")
project_name = st.selectbox("Select Project", projects["name"])
project_id = projects.set_index("name").loc[project_name]["id"]

# ---------------- ADMIN PANEL ----------------
if st.session_state.admin:
    with st.sidebar.expander("Admin Panel", expanded=True):

        # Add Project
        new_proj = st.text_input("New Project Name")
        if st.button("Add Project"):
            exec_query("INSERT INTO projects(name) VALUES(:n)", {"n": new_proj})
            st.rerun()

        # Add Plot
        st.markdown("---")
        plot_no = st.number_input("Plot Number", min_value=1)
        status = st.selectbox("Status", ["Available", "Booked", "Sold"])
        cust = st.text_input("Customer Name (if booked/sold)")
        if st.button("Add Plot"):
            exec_query(
                """INSERT INTO plots(project_id,plot_number,status,customer_name)
                   VALUES(:pid,:pn,:st,:cn)""",
                {"pid": project_id, "pn": plot_no, "st": status, "cn": cust}
            )
            st.rerun()

# ---------------- PLOTS VIEW ----------------
plots = query_df(
    "SELECT plot_number,status,customer_name FROM plots WHERE project_id=:p ORDER BY plot_number",
    {"p": project_id}
)

st.subheader(f"📍 Plot Map – {project_name}")
st.markdown('<div class="plot-grid">', unsafe_allow_html=True)

for _, r in plots.iterrows():
    tip = f"title='Customer: {r.customer_name}'" if r.customer_name else ""
    st.markdown(
        f"<div class='plot {r.status}' {tip}>{r.plot_number}</div>",
        unsafe_allow_html=True
    )

st.markdown("</div>", unsafe_allow_html=True)

# ---------------- FOOTER ----------------
st.markdown('<div class="footer">Built by <a href="https://aiclex.in">AICLEX TECHNOLOGIES</a></div>', unsafe_allow_html=True)
