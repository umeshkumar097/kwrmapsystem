import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# --- पेज का कॉन्फ़िगरेशन ---
st.set_page_config(page_title="KWR PLOT MAP", layout="wide")

# --- CSS for Responsive Grid and Custom Tooltip ---
st.markdown("""
<style>
.plot-grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(70px, 1fr)); /* बदला हुआ: 90px से 70px */
    gap: 10px; /* बदला हुआ: गैप थोड़ा कम किया */
    padding: 10px 0;
}
/* Main box for the plot */
.plot-box {
    position: relative;
    padding: 15px 5px; /* बदला हुआ: ऊंचाई कम करने के लिए 20px से 15px */
    border-radius: 8px; /* बदला हुआ: थोड़ा कम गोल */
    color: white;
    text-align: center;
    font-size: 20px; /* बदला हुआ: नंबर का साइज़ 24px से 20px */
    font-weight: bold;
    cursor: default;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
}
/* The tooltip text (hidden by default) */
.plot-box .tooltiptext {
    visibility: hidden;
    width: 200px;
    background-color: #555;
    color: #fff;
    text-align: left;
    border-radius: 6px;
    padding: 8px 12px;
    position: absolute;
    z-index: 1;
    bottom: 125%;
    left: 50%;
    margin-left: -100px;
    opacity: 0;
    transition: opacity 0.3s;
    font-size: 14px;
    font-weight: normal;
}
/* Show the tooltip text on hover (for desktop) and on active (for mobile tap-and-hold) */
.plot-box:hover .tooltiptext, .plot-box:active .tooltiptext {
    visibility: visible;
    opacity: 1;
}
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
                else:
                    st.warning("Project name is empty or already exists.")
    
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
    st.info("No projects found. Please add a project via the Admin Panel.")

# --- फुटर ---
st.markdown("---")
st.markdown('<div class="footer">BUILD BY <a href="http://www.aiclex.in" target="_blank">AICLEX TECHNOLOGIES</a></div>', unsafe_allow_html=True)
