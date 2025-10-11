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
            st.cache_resource.clear() # Clear all caches on write
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
                return pd.read_sql("SELECT id, phone_number FROM users ORDER BY phone_number;", connection)
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

if not st.session_state.logged_in_user:
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
    st.sidebar.success(f"Logged in as: {st.session_state.logged_in_user}")
    if st.sidebar.button("Logout"):
        del st.session_state.logged_in_user
        if 'admin_logged_in' in st.session_state:
            del st.session_state.admin_logged_in
        st.rerun()

    st.title("KWR PLOT MAP")

    # --- Admin Login ---
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
            
            st.markdown("---")
            st.subheader("Manage Existing Users")
            all_users = get_all_users()
            if not all_users.empty:
                user_to_manage = st.selectbox("Select User", options=all_users['phone_number'])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Delete User", use_container_width=True):
                        st.session_state.user_to_delete = user_to_manage
                if 'user_to_delete' in st.session_state and st.session_state.user_to_delete == user_to_manage:
                     st.warning(f"Are you sure you want to delete {user_to_manage}?")
                     if st.button("Confirm Deletion", use_container_width=True, type="primary"):
                        run_query("DELETE FROM users WHERE phone_number = :phone", {'phone': user_to_manage})
                        st.success(f"User {user_to_manage} deleted.")
                        del st.session_state.user_to_delete
                        st.rerun()
                with col2:
                     if st.button("Change Password", use_container_width=True):
                        st.session_state.user_to_change_pw = user_to_manage
                if 'user_to_change_pw' in st.session_state and st.session_state.user_to_change_pw == user_to_manage:
                    with st.form("change_password_form"):
                        new_pw = st.text_input("Enter New Password", type="password")
                        if st.form_submit_button("Update Password"):
                            if new_pw:
                                hashed_pw = hash_password(new_pw).decode('utf-8')
                                run_query("UPDATE users SET password_hash = :pw_hash WHERE phone_number = :phone", {'pw_hash': hashed_pw, 'phone': user_to_manage})
                                st.success(f"Password for {user_to_manage} updated.")
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
    
        with st.sidebar.expander("Create New Project"):
            new_project_name = st.text_input("New Project Name")
            if st.button("Create Project"):
                if new_project_name and new_project_name not in project_names_admin:
                    run_query("INSERT INTO projects (name) VALUES (:name)", {'name': new_project_name})
                    st.success(f"Project '{new_project_name}' created!")
                    st.rerun()
                else:
                    st.warning("Project name is empty or already exists.")

        selected_project_admin = st.sidebar.selectbox("Select Project to Manage", options=project_names_admin, index=0 if project_names_admin else None)

        if selected_project_admin:
            with st.sidebar.expander(f"Delete Project: {selected_project_admin}"):
                st.warning(f"DANGER ZONE: This will delete the project and all its plots forever.")
                if st.button("Confirm Deletion of Project", type="primary"):
                    project_id_to_delete = project_id_map_admin[selected_project_admin]
                    run_query("DELETE FROM projects WHERE id = :id", {'id': project_id_to_delete})
                    st.success(f"Project '{selected_project_admin}' deleted.")
                    st.rerun()

            st.sidebar.markdown("---")
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
                        run_query(query, params)
                        st.success(f"Plot {new_plot_number} added!")
                        st.rerun()

                st.markdown("---")
                st.subheader("Delete Plot")
                plot_to_delete = st.selectbox("Select Plot to Delete", options=plot_numbers_admin, key="delete_select")
                if st.button("Delete Selected Plot", type="primary"):
                    if plot_to_delete:
                        plot_id_to_delete = plot_id_map_admin_plots[plot_to_delete]
                        run_query("DELETE FROM plots WHERE id = :id", {'id': plot_id_to_delete})
                        st.warning(f"Plot {plot_to_delete} deleted.")
                        st.rerun()

    # --- User UI ---
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
