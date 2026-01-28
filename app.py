import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import bcrypt
from datetime import datetime, timedelta

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
            st.cache_resource.clear()
            return True
        except Exception as e:
            st.error(f"Database Query Error: {e}")
            init_connection.clear()
            return False

@st.cache_data(ttl=60)
def get_all_users():
    engine = init_connection()
    if engine:
        try:
            with engine.connect() as connection:
                return pd.read_sql("SELECT id, name, phone_number FROM users ORDER BY name;", connection)
        except Exception as e:
            st.error(f"Failed to fetch users: {e}")
            init_connection.clear()
            return pd.DataFrame()
    return pd.DataFrame()

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

# --- Last Seen Functions ---
def update_last_seen(phone_number):
    run_query("UPDATE users SET last_seen = NOW() WHERE phone_number = :phone", {'phone': phone_number})

@st.cache_data(ttl=15)
def get_live_users():
    engine = init_connection()
    if engine:
        try:
            with engine.connect() as connection:
                query = text("SELECT name, phone_number FROM users WHERE last_seen >= NOW() - INTERVAL 1 MINUTE")
                return pd.read_sql(query, connection)
        except Exception:
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
            query = text("SELECT name, password_hash, is_admin FROM users WHERE phone_number = :phone")
            result = connection.execute(query, {'phone': phone}).fetchone()
            if result and check_password(password, result[1]):
                st.session_state['logged_in_user_name'] = result[0] or phone
                st.session_state['logged_in_user_phone'] = phone
                st.session_state['is_admin'] = bool(result[2])
                update_last_seen(phone)
                st.rerun()
            else:
                st.error("Invalid phone number or password.")

# --- Main App Logic ---
if 'logged_in_user_phone' not in st.session_state:
    st.session_state.logged_in_user_phone = None
    st.session_state.is_admin = False

if not st.session_state.logged_in_user_phone:
    # --- Login Page ---
    st.title("Login to KWR PLOT MAP")
    with st.form("login_form"):
        phone = st.text_input("Phone Number")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            login_user(phone, password)
    st.markdown("---")
    st.markdown('<div class="footer">BUILD BY <a href="http://www.aiclex.in" target="_blank">AICLEX TECHNOLOGIES</a></div>', unsafe_allow_html=True)

else:
    # --- Main App UI (if user is logged in) ---
    update_last_seen(st.session_state.logged_in_user_phone)

    st.sidebar.success(f"Logged in as: {st.session_state.logged_in_user_name}")
    if st.session_state.is_admin:
        st.sidebar.warning("Admin Access Granted")
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- THIS IS THE NEW WELCOME MESSAGE ---
    st.subheader(f"Hi {st.session_state.logged_in_user_name}, welcome 👋")

    st.title("KWR PLOT MAP")

    # --- Admin Controls (Only if admin is logged in) ---
    if st.session_state.is_admin:
        st.sidebar.header("🔑 Admin Panel")
        st.sidebar.markdown("---")
        
        with st.sidebar.expander("Live User Status"):
            live_users_df = get_live_users()
            if not live_users_df.empty:
                st.write("Currently Active Users:")
                for index, user in live_users_df.iterrows():
                    display_name = user['name'] or user['phone_number']
                    st.write(f"- {display_name}")
            else:
                st.write("No users are currently active.")
            if st.button("Refresh Status"):
                st.rerun()
        
        with st.sidebar.expander("User Management"):
            st.subheader("Register New User")
            with st.form("register_form", clear_on_submit=True):
                new_name = st.text_input("New User's Name")
                new_phone = st.text_input("New User Phone Number")
                new_password = st.text_input("New User Password", type="password")
                is_admin_checkbox = st.checkbox("Make this user an admin")
                if st.form_submit_button("Register User"):
                    if new_phone and new_password and new_name:
                        hashed_pw = hash_password(new_password).decode('utf-8')
                        query = "INSERT INTO users (name, phone_number, password_hash, is_admin) VALUES (:name, :phone, :pw_hash, :is_admin)"
                        params = {'name': new_name, 'phone': new_phone, 'pw_hash': hashed_pw, 'is_admin': is_admin_checkbox}
                        if run_query(query, params):
                            st.success(f"User '{new_name}' registered successfully!")
                        else:
                            st.error("This phone number might already be registered.")
                    else:
                        st.warning("Name, phone, and password cannot be empty.")
            
            st.markdown("---")
            st.subheader("Manage Existing Users")
            all_users = get_all_users()
            if not all_users.empty:
                all_users['display'] = all_users.apply(lambda row: f"{row['name']} ({row['phone_number']})", axis=1)
                user_display_to_manage = st.selectbox("Select User", options=all_users['display'])
                
                selected_phone = all_users[all_users['display'] == user_display_to_manage]['phone_number'].iloc[0]

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Delete User", use_container_width=True, type="primary"):
                        if selected_phone == 'admin':
                            st.error("The default admin user cannot be deleted.")
                        else:
                            run_query("DELETE FROM users WHERE phone_number = :phone", {'phone': selected_phone})
                            st.success(f"User {selected_phone} deleted.")
                            st.rerun()
                with col2:
                    if st.button("Change Password", use_container_width=True):
                        st.session_state.user_to_change_pw = selected_phone
                
                if 'user_to_change_pw' in st.session_state and st.session_state.user_to_change_pw == selected_phone:
                    with st.form("change_password_form"):
                        new_pw = st.text_input("Enter New Password", type="password")
                        if st.form_submit_button("Update Password"):
                            if new_pw:
                                hashed_pw = hash_password(new_pw).decode('utf-8')
                                run_query("UPDATE users SET password_hash = :pw_hash WHERE phone_number = :phone", {'pw_hash': hashed_pw, 'phone': selected_phone})
                                st.success(f"Password for {selected_phone} updated.")
                                del st.session_state.user_to_change_pw
                            else:
                                st.warning("Password cannot be empty.")
            else:
                st.info("No users registered yet.")

        st.sidebar.markdown("---")
        st.sidebar.subheader("Project Management")
        projects_df_admin = get_all_projects()
        project_names_admin = projects_df_admin['name'].tolist() if not projects_df_admin.empty else []
        project_id_map_admin = pd.Series(projects_df_admin.id.values, index=projects_df_admin.name).to_dict() if not projects_df_admin.empty else {}
    
        with st.sidebar.expander("Manage Projects"):
            st.subheader("Create New Project")
            new_project_name = st.text_input("New Project Name")
            if st.button("Create Project"):
                if new_project_name and new_project_name not in project_names_admin:
                    run_query("INSERT INTO projects (name) VALUES (:name)", {'name': new_project_name})
                    st.success(f"Project '{new_project_name}' created!")
                    st.rerun()
                else:
                    st.warning("Project name is empty or already exists.")
            
            st.markdown("---")
            st.subheader("Edit or Delete Project")
            project_to_manage_name = st.selectbox("Select Project", options=project_names_admin)
            
            if project_to_manage_name:
                new_name_for_edit = st.text_input("Enter new name to update", value=project_to_manage_name)
                if st.button("Update Name"):
                    if new_name_for_edit and new_name_for_edit != project_to_manage_name:
                        project_id_to_edit = project_id_map_admin[project_to_manage_name]
                        run_query("UPDATE projects SET name = :new_name WHERE id = :id", {'new_name': new_name_for_edit, 'id': project_id_to_edit})
                        st.success(f"Project name updated to '{new_name_for_edit}'!")
                        st.rerun()
                    else:
                        st.warning("New name is empty or same as the old name.")

                if st.button("Delete Project", type="primary"):
                    project_id_to_delete = project_id_map_admin[project_to_manage_name]
                    run_query("DELETE FROM projects WHERE id = :id", {'id': project_id_to_delete})
                    st.success(f"Project '{project_to_manage_name}' deleted.")
                    st.rerun()

        st.sidebar.markdown("---")
        selected_project_admin = st.sidebar.selectbox("Select Project to Manage Plots", options=project_names_admin, index=0 if project_names_admin else None)
        if selected_project_admin:
            st.sidebar.subheader(f"Manage Plots for: {selected_project_admin}")
            selected_project_id_admin = project_id_map_admin[selected_project_admin]
            plots_df_admin = get_plots_for_project(selected_project_id_admin)
            plot_numbers_admin = plots_df_admin['plot_number'].tolist() if not plots_df_admin.empty else []
            plot_id_map_admin_plots = pd.Series(plots_df_admin.id.values, index=plots_df_admin.plot_number).to_dict() if not plots_df_admin.empty else {}

            with st.sidebar.expander("Update, Add, or Delete Plots", expanded=True):
                st.subheader("Update Plot Status")
                selected_plot_update = st.selectbox("Select Plot to Update", options=plot_numbers_admin, key="update_select")
                statuses = ["Available", "Booked", "Sold"]
                new_status = st.selectbox("Select New Status", options=statuses)
                customer_name_update = ""
                if new_status in ["Booked", "Sold"]:
                    customer_name_update = st.text_input("Customer Name", key="update_customer_name")
                if st.button("Update Status"):
                    if selected_plot_update:
                        plot_id_to_update = plot_id_map_admin_plots[selected_plot_update]
                        company_name_update = "KWR GROUP" if new_status in ["Booked", "Sold"] else ""
                        query = "UPDATE plots SET status = :status, customer_name = :c_name, company_name = :co_name WHERE id = :id"
                        params = {'status': new_status, 'c_name': customer_name_update, 'co_name': company_name_update, 'id': plot_id_to_update}
                        run_query(query, params)
                        st.success("Plot updated!")
                        st.rerun()
                
                st.markdown("---")
                st.subheader("Add New Plot")
                new_plot_number = st.number_input("Enter New Plot Number", min_value=1, step=1)
                initial_status = st.selectbox("Initial Status", options=statuses, key="add_status")
                customer_name_add = ""
                if initial_status in ["Booked", "Sold"]:
                    customer_name_add = st.text_input("Customer Name", key="add_customer_name")
                if st.button("Add Plot"):
                    if new_plot_number in plot_numbers_admin:
                        st.error(f"Plot {new_plot_number} already exists in this project!")
                    else:
                        company_name_add = "KWR GROUP" if initial_status in ["Booked", "Sold"] else None
                        query = "INSERT INTO plots (project_id, plot_number, status, customer_name, company_name) VALUES (:proj_id, :p_num, :stat, :c_name, :co_name)"
                        params = {'proj_id': selected_project_id_admin, 'p_num': new_plot_number, 'stat': initial_status, 'c_name': customer_name_add, 'co_name': company_name_add}
                        run_query(query,
