import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# --- पेज का कॉन्फ़िगरेशन ---
st.set_page_config(page_title="KWR PLOT MAP", layout="wide")

# --- CSS ---
st.markdown("""
<style>
.plot-grid-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); gap: 15px; padding: 10px 0; }
.plot-box { padding: 20px 5px; border-radius: 10px; color: white; text-align: center; font-size: 24px; font-weight: bold; box-shadow: 2px 2px 5px rgba(0,0,0,0.2); transition: transform 0.2s; }
.plot-box:hover { transform: scale(1.05); }
a.plot-link { text-decoration: none; }
.footer { text-align: center; padding: 20px 0; color: #888; }
.footer a { color: #007bff; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# --- SQLAlchemy डेटाबेस कनेक्शन ---
@st.cache_resource(ttl=600)
def init_connection():
    try:
        db_secrets = st.secrets["mysql"]
        db_uri = f"mysql+pymysql://{db_secrets['user']}:{db_secrets['password']}@{db_secrets['host']}:{db_secrets['port']}/{db_secrets['database']}"
        engine = create_engine(db_uri)
        return engine
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

# --- डेटाबेस फंक्शन्स ---
def run_query(query, params=None):
    engine = init_connection()
    if engine:
        try:
            with engine.connect() as connection:
                connection.execute(text(query), params)
                connection.commit()
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Database Query Error: {e}")
            return False

@st.cache_data(ttl=60)
def get_all_projects():
    engine = init_connection()
    if engine:
        with engine.connect() as connection:
            return pd.read_sql("SELECT id, name FROM projects ORDER BY name;", connection)
    return pd.DataFrame()

@st.cache_data(ttl=60)
def get_plots_for_project(project_id):
    if not project_id: return pd.DataFrame()
    engine = init_connection()
    if engine:
        with engine.connect() as connection:
            query = text("SELECT id, plot_number, status, customer_name, company_name FROM plots WHERE project_id = :proj_id ORDER BY plot_number;")
            return pd.read_sql(query, connection, params={"proj_id": project_id})
    return pd.DataFrame()

# --- मुख्य UI ---
st.title("KWR PLOT MAP")

# --- एडमिन लॉगइन ---
st.sidebar.header("🔑 Admin Panel")
password = st.sidebar.text_input("Enter Admin Password", type="password")
if password == st.secrets["admin"]["password"]: st.session_state['logged_in'] = True
elif password:
    st.sidebar.error("❌ Incorrect password.")
    if 'logged_in' in st.session_state: del st.session_state['logged_in']

# --- एडमिन कंट्रोल ---
if st.session_state.get('logged_in', False):
    # ... (एडमिन पैनल का पूरा कोड यहाँ आएगा, जैसा पहले था) ...
    st.sidebar.subheader("Project Management")
    projects_df_admin = get_all_projects()
    project_names_admin = projects_df_admin['name'].tolist() if not projects_df_admin.empty else []
    project_id_map_admin = pd.Series(projects_df_admin.id.values, index=projects_df_admin.name).to_dict() if not projects_df_admin.empty else {}
    selected_project_admin = st.sidebar.selectbox("Select Project to Manage", options=project_names_admin, index=0 if project_names_admin else None)
    col1, col2 = st.sidebar.columns(2)
    if col1.button("New Project"): st.session_state.show_new_project_dialog = True
    if col2.button("Delete Project", disabled=not selected_project_admin): st.session_state.show_delete_project_dialog = True
    if st.session_state.get("show_new_project_dialog", False):
        with st.dialog("Create New Project"):
            new_project_name = st.text_input("Project Name")
            if st.button("Create"):
                if new_project_name and new_project_name not in project_names_admin:
                    run_query("INSERT INTO projects (name) VALUES (:name)", {'name': new_project_name})
                    del st.session_state.show_new_project_dialog
                    st.rerun()
                else: st.warning("Project name is empty or already exists.")
    if st.session_state.get("show_delete_project_dialog", False):
        with st.dialog("Confirm Deletion"):
            st.warning(f"Are you sure you want to delete '{selected_project_admin}'? All its plots will be deleted forever.")
            if st.button("Yes, Delete Permanently"):
                project_id_to_delete = project_id_map_admin[selected_project_admin]
                run_query("DELETE FROM projects WHERE id = :id", {'id': project_id_to_delete})
                del st.session_state.show_delete_project_dialog
                st.rerun()
    if selected_project_admin:
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
            customer_name, company_name = "", ""
            if new_status in ["Booked", "Sold"]:
                customer_name = st.text_input("Customer Name")
                company_name = st.text_input("Company Name")
            if st.button("Update Status"):
                if selected_plot_update:
                    plot_id_to_update = plot_id_map_admin_plots[selected_plot_update]
                    query = "UPDATE plots SET status = :status, customer_name = :c_name, company_name = :co_name WHERE id = :id"
                    params = {'status': new_status, 'c_name': customer_name, 'co_name': company_name, 'id': plot_id_to_update}
                    run_query(query, params)
                    st.success("Plot updated!")
                    st.rerun()
            st.subheader("Add New Plot")
            new_plot_number = st.number_input("Enter New Plot Number", min_value=1, step=1)
            initial_status = st.selectbox("Initial Status", options=statuses, key="add_status")
            if st.button("Add Plot"):
                if new_plot_number in plot_numbers_admin:
                    st.error(f"Plot {new_plot_number} already exists!")
                else:
                    query = "INSERT INTO plots (project_id, plot_number, status) VALUES (:proj_id, :p_num, :stat)"
                    params = {'proj_id': selected_project_id_admin, 'p_num': new_plot_number, 'stat': initial_status}
                    run_query(query, params)
                    st.success(f"Plot {new_plot_number} added!")
                    st.rerun()
            st.subheader("Delete Plot")
            plot_to_delete = st.selectbox("Select Plot to Delete", options=plot_numbers_admin, key="delete_select")
            if st.button("Delete Selected Plot"):
                if plot_to_delete:
                    plot_id_to_delete = plot_id_map_admin_plots[plot_to_delete]
                    run_query("DELETE FROM plots WHERE id = :id", {'id': plot_id_to_delete})
                    st.warning(f"Plot {plot_to_delete} deleted.")
                    st.rerun()

# --- यूजर के लिए UI ---
projects_df = get_all_projects()
if not projects_df.empty:
    project_names = projects_df['name'].tolist()
    project_id_map = pd.Series(projects_df.id.values, index=projects_df.name).to_dict()
    selected_project_name = st.selectbox("Select a Project to View", options=project_names)
    
    if selected_project_name:
        selected_project_id = project_id_map[selected_project_name]
        plots_df = get_plots_for_project(selected_project_id)
        st.subheader(f"Plot Availability for: {selected_project_name}")
        
        if plots_df.empty:
            st.info("No plots found for this project.")
        else:
            # --- रंगीन और clickable ग्रिड बनाने का सही तरीका ---
            STATUS_COLORS = {"Available": "#28a745", "Booked": "#ffc107", "Sold": "#dc3545"}
            
            html_plots = []
            for index, row in plots_df.iterrows():
                color = STATUS_COLORS.get(row['status'], "#6c757d")
                plot_html = f'<div class="plot-box" style="background-color: {color};">{row.plot_number}</div>'
                
                # Booked या Sold होने पर ही लिंक बनाएं
                if row['status'] in ["Booked", "Sold"]:
                    # URL में plot_id डालें
                    html_plots.append(f'<a href="?project={selected_project_name}&plot_id={row.id}" class="plot-link">{plot_html}</a>')
                else:
                    html_plots.append(plot_html)
            
            st.markdown(f'<div class="plot-grid-container">{"".join(html_plots)}</div>', unsafe_allow_html=True)

            # --- क्लिक किए गए प्लॉट की जानकारी नीचे दिखाएं ---
            query_params = st.query_params
            if "plot_id" in query_params:
                try:
                    plot_id_to_show = int(query_params.get("plot_id"))
                    plot_details = plots_df[plots_df['id'] == plot_id_to_show].iloc[0]
                    
                    with st.container(border=True):
                        st.subheader(f"Details for Plot #{plot_details['plot_number']}")
                        details_md = f"""
                        - **Status:** {plot_details['status']}
                        - **Customer Name:** {plot_details['customer_name'] or 'N/A'}
                        - **Company Name:** {plot_details['company_name'] or 'N/A'}
                        """
                        st.markdown(details_md)
                        if st.button("Close"):
                            st.query_params.clear()
                except (ValueError, IndexError):
                    pass # अगर गलत plot_id हो तो कुछ न करें
else:
    st.info("No projects found. Please add a project via the Admin Panel.")

# --- फुटर ---
st.markdown("---")
st.markdown('<div class="footer">BUILD BY <a href="http://www.aiclex.in" target="_blank">AICLEX TECHNOLOGIES</a></div>', unsafe_allow_html=True)
