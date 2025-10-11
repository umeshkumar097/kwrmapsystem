import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import bcrypt

# --- Page Configuration ---
st.set_page_config(page_title="KWR PLOT MAP", layout="wide")

# --- CSS ---
st.markdown("""
<style>
.plot-grid-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(70px, 1fr)); gap: 10px; padding: 10px 0; }
.plot-box { position: relative; padding: 15px 5px; border-radius: 8px; color: white; text-align: center; font-size: 20px; font-weight: bold; cursor: default; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); }
.plot-box .tooltiptext { visibility: hidden; width: 200px; background-color: #555; color: #fff; text-align: left; border-radius: 6px; padding: 8px 12px; position: absolute; z-index: 1; bottom: 125%; left: 50%; margin-left: -100px; opacity: 0; transition: opacity 0.3s; font-size: 14px; font-weight: normal; }
.plot-box:hover .tooltiptext, .plot-box:active .tooltiptext { visibility: visible; opacity: 1; }
.footer { text-align: center; padding: 20px 0; color: #888; }
.footer a { color: #007bff; text-decoration: none; }
</style>
""", unsafe_allow_html=True)


# --- Password Hashing Functions ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed_password_from_db):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password_from_db.encode('utf-8'))

# --- Database Connection ---
@st.cache_resource(ttl=600)
def init_connection():
    try:
        db_secrets = st.secrets["mysql"]
        db_uri = f"mysql+pymysql://{db_secrets['user']}:{db_secrets['password']}@{db_secrets['host']}:{db_secrets['port']}/{db_secrets['database']}"
        engine = create_engine(db_uri, pool_recycle=280, pool_pre_ping=True)
        return engine
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

# --- Database Functions ---
def run_query(query, params=None):
    engine = init_connection()
    if not engine: return False
    with engine.connect() as connection:
        try:
            with connection.begin() as trans:
                connection.execute(text(query), params)
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Database Query Error: {e}")
            init_connection.clear()
            return False

@st.cache_data(ttl=60)
def get_all_projects():
    engine = init_connection()
    if engine:
        try:
            with engine.connect() as connection:
                return pd.read_sql("SELECT id, name FROM projects ORDER BY name;", connection)
        except Exception as e:
            st.error(f"Failed to fetch projects: {e}")
            init_connection.clear()
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=60)
def get_plots_for_project(project_id):
    if not project_id: return pd.DataFrame()
    engine = init_connection()
    if engine:
        try:
            with engine.connect() as connection:
                query = text("SELECT id, plot_number, status, customer_name, company_name FROM plots WHERE project_id = :proj_id ORDER BY plot_number;")
                return pd.read_sql(query, connection, params={"proj_id": project_id})
        except Exception as e:
            st.error(f"Failed to fetch plots: {e}")
            init_connection.clear()
            return pd.DataFrame()
    return pd.DataFrame()

# --- Login Function ---
def login_user(phone, password):
    if not phone or not password:
        st.error("Phone number and password are required.")
        return
    engine = init_connection()
    if engine:
        with engine.connect() as connection:
            query = text("SELECT password_hash FROM users WHERE phone_number = :phone")
            result = connection.execute(query, {'phone': phone}).fetchone()
            if result and check_password(password, result[0]):
                st.session_state['logged_in_user'] = phone
                st.rerun()
            else:
                st.error("Invalid phone number or password.")

# --- Main App Logic ---
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None

# --- Admin Panel (ALWAYS VISIBLE) ---
st.sidebar.header("🔑 Admin Panel")
admin_password = st.sidebar.text_input("Enter Admin Password", type="password", key="admin_pw")
if admin_password == st.secrets["admin"]["password"]:
    st.session_state['admin_logged_in'] = True
elif admin_password:
    st.sidebar.error("❌ Incorrect password.")
    if 'admin_logged_in' in st.session_state:
        del st.session_state.admin_logged_in

# --- Admin Controls (Only if admin is logged in) ---
if st.session_state.get('admin_logged_in', False):
    st.sidebar.markdown("---")
    with st.sidebar.expander("User Management"):
        st.subheader("Register New User")
        with st.form("register_form", clear_on_submit=True):
            new_phone = st.text_input("New User Phone Number")
            new_password = st.text_input("New User Password", type="password")
            if st.form_submit_button("Register User"):
                if new_phone and new_password:
                    hashed_pw = hash_password(new_password).decode('utf-8')
                    query = "INSERT INTO users (phone_number, password_hash) VALUES (:phone, :pw_hash)"
                    if run_query(query, {'phone': new_phone, 'pw_hash': hashed_pw}):
                        st.success(f"User '{new_phone}' registered successfully!")
                    else:
                        st.error("This phone number might already be registered.")
                else:
                    st.warning("Phone number and password cannot be empty.")
    st.sidebar.markdown("---")
    st.sidebar.subheader("Project Management")
    # ... (Rest of the admin controls for projects and plots)

# --- Main Content Area ---
if not st.session_state.logged_in_user:
    # --- Login Page ---
    st.title("Login to KWR PLOT MAP")
    with st.form("login_form"):
        phone = st.text_input("Phone Number")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            login_user(phone, password)
else:
    # --- Main App UI (if user is logged in) ---
    st.sidebar.success(f"Logged in as: {st.session_state.logged_in_user}")
    if st.sidebar.button("Logout"):
        del st.session_state.logged_in_user
        if 'admin_logged_in' in st.session_state:
            del st.session_state.admin_logged_in
        st.rerun()

    st.title("KWR PLOT MAP- BLOCK -A")
    
    projects_df = get_all_projects()
    if not projects_df.empty:
        project_names = projects_df['name'].tolist()
        project_id_map = pd.Series(projects_df.id.values, index=projects_df.name).to_dict()
        selected_project_name = st.selectbox("Select a Project to View", options=project_names)
        
        st.markdown("""
        <div style="display: flex; justify-content: center; align-items: center; gap: 20px; padding: 10px 0; border-top: 1px solid #eee; border-bottom: 1px solid #eee; margin: 15px 0;">
            <div style="display: flex; align-items: center;"><div style="width:20px; height:20px; background-color:#28a745; border-radius:3px; margin-right: 8px;"></div><b>Available</b></div>
            <div style="display: flex; align-items: center;"><div style="width:20px; height:20px; background-color:#ffc107; border-radius:3px; margin-right: 8px;"></div><b>Booked</b></div>
            <div style="display: flex; align-items: center;"><div style="width:20px; height:20px; background-color:#dc3545; border-radius:3px; margin-right: 8px;"></div><b>Sold</b></div>
        </div>
        """, unsafe_allow_html=True)
        
        if selected_project_name:
            selected_project_id = project_id_map[selected_project_name]
            plots_df = get_plots_for_project(selected_project_id)
            st.subheader(f"Plot Availability for: {selected_project_name}")
            
            if plots_df.empty:
                st.info("No plots found for this project.")
            else:
                STATUS_COLORS = {"Available": "#28a745", "Booked": "#ffc107", "Sold": "#dc3545"}
                html_plots = []
                for index, row in plots_df.iterrows():
                    color = STATUS_COLORS.get(row['status'], "#6c757d")
                    tooltip_content = ""
                    if row['status'] in ["Booked", "Sold"]:
                        c_name = row['customer_name'] or "N/A"
                        co_name = row['company_name'] or "N/A"
                        tooltip_content = f"Name: {c_name}<br>Company: {co_name}"
                    
                    if row['status'] in ["Booked", "Sold"]:
                        plot_html = f'<div class="plot-box" style="background-color: {color};">{row.plot_number}<span class="tooltiptext">{tooltip_content}</span></div>'
                        html_plots.append(plot_html)
                    else:
                        html_plots.append(f'<div class="plot-box" style="background-color: {color};">{row.plot_number}</div>')

                st.markdown(f'<div class="plot-grid-container">{"".join(html_plots)}</div>', unsafe_allow_html=True)
    else:
        st.info("No projects found. Please add a project from the Admin Panel if you are an admin.")

    # --- Footer ---
    st.markdown("---")
    st.markdown('<div class="footer">BUILD BY <a href="http://www.aiclex.in" target="_blank">AICLEX TECHNOLOGIES</a></div>', unsafe_allow_html=True)
