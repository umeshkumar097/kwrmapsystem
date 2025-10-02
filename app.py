import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# --- पेज का कॉन्फ़िगरेशन ---
# ब्राउज़र टैब का टाइटल यहाँ सेट होता है
st.set_page_config(page_title="KWR PLOT MAP", layout="wide")

# --- Responsive Grid और Footer के लिए CSS ---
st.markdown("""
<style>
.plot-grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
    gap: 15px;
    padding: 10px 0;
}
.plot-box {
    padding: 20px 5px;
    border-radius: 10px;
    color: white;
    text-align: center;
    font-size: 24px;
    font-weight: bold;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    transition: transform 0.2s;
}
.plot-box:hover {
    transform: scale(1.05);
}
a.plot-link {
    text-decoration: none;
}
.footer {
    text-align: center;
    padding: 20px 0;
    color: #888;
}
.footer a {
    color: #007bff;
    text-decoration: none;
}
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
@st.cache_data(ttl=60)
def get_all_plots():
    engine = init_connection()
    if engine:
        try:
            with engine.connect() as connection:
                query = "SELECT id, plot_number, status, customer_name, company_name FROM plots ORDER BY plot_number;"
                df = pd.read_sql(query, connection)
                return df
        except Exception as e:
            st.error(f"Error fetching data: {e}")
    return pd.DataFrame()

def run_query(query, params=None):
    engine = init_connection()
    if engine:
        try:
            with engine.connect() as connection:
                connection.execute(text(query), params)
                connection.commit()
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Database Query Error: {e}")

# --- मुख्य ऐप का UI ---
# 1. मुख्य टाइटल यहाँ बदला गया है
st.title("KWR PLOT MAP")

# --- एडमिन लॉगइन (साइडबार में) ---
# ... (एडमिन पैनल का पूरा कोड यहाँ आएगा, जैसा पहले था वैसा ही) ...
st.sidebar.header("🔑 Admin Panel")
password = st.sidebar.text_input("Enter Admin Password", type="password")

if password == st.secrets["admin"]["password"]:
    st.session_state['logged_in'] = True
    st.sidebar.success("✅ Logged in successfully!")
elif password:
    st.sidebar.error("❌ Incorrect password.")
    if 'logged_in' in st.session_state:
        del st.session_state['logged_in']

if st.session_state.get('logged_in', False):
    plots_df_admin = get_all_plots()
    plot_numbers = plots_df_admin['plot_number'].tolist() if not plots_df_admin.empty else []
    plot_id_map = pd.Series(plots_df_admin.id.values, index=plots_df_admin.plot_number).to_dict() if not plots_df_admin.empty else {}
    st.sidebar.subheader("Update Plot Status")
    selected_plot_update = st.sidebar.selectbox("Select Plot to Update", options=plot_numbers, key="update_select")
    statuses = ["Available", "Booked", "Sold"]
    new_status = st.sidebar.selectbox("Select New Status", options=statuses)
    customer_name = ""
    company_name = ""
    if new_status in ["Booked", "Sold"]:
        st.sidebar.write("Enter Customer Details (Optional)")
        customer_name = st.sidebar.text_input("Customer Name")
        company_name = st.sidebar.text_input("Company Name")
    if st.sidebar.button("Update Status"):
        if selected_plot_update:
            plot_id_to_update = plot_id_map[selected_plot_update]
            query = "UPDATE plots SET status = :status, customer_name = :c_name, company_name = :co_name WHERE id = :id"
            params = {'status': new_status, 'c_name': customer_name, 'co_name': company_name, 'id': plot_id_to_update}
            run_query(query, params)
            st.sidebar.success(f"Plot {selected_plot_update} updated!")
            st.rerun()

# --- प्लॉट्स को ग्रिड में दिखाएं ---
st.subheader("Current Plot Availability")
clicked_plot_number_str = st.query_params.get("plot", [None])[0]
plots_df = get_all_plots()

if plots_df.empty and not st.session_state.get('logged_in', False):
    st.warning("Could not load plot data.")
else:
    STATUS_COLORS = {"Available": "#28a745", "Booked": "#ffc107", "Sold": "#dc3545"}
    html_plots = []
    for index, row in plots_df.iterrows():
        plot_number, status = row['plot_number'], row['status']
        color = STATUS_COLORS.get(status, "#6c757d")
        plot_html = f'<div class="plot-box" style="background-color: {color};">{plot_number}</div>'
        if status in ["Booked", "Sold"]:
             html_plots.append(f'<a href="?plot={plot_number}" class="plot-link">{plot_html}</a>')
        else:
            html_plots.append(plot_html)
    st.markdown(f'<div class="plot-grid-container">{"".join(html_plots)}</div>', unsafe_allow_html=True)
    
    if clicked_plot_number_str:
        try:
            clicked_plot_number = int(clicked_plot_number_str)
            plot_details = plots_df[plots_df['plot_number'] == clicked_plot_number].iloc[0]
            st.subheader(f"Details for Plot #{plot_details['plot_number']}")
            details_md = f"""
            - **Status:** {plot_details['status']}
            - **Customer Name:** {plot_details['customer_name'] or 'N/A'}
            - **Company Name:** {plot_details['company_name'] or 'N/A'}
            """
            st.info(details_md)
        except (ValueError, IndexError):
            pass

# --- 2. फुटर यहाँ जोड़ा गया है ---
st.markdown("---")
st.markdown('<div class="footer">BUILD BY <a href="http://www.aiclex.in" target="_blank">AICLEX TECHNOLOGIES</a></div>', unsafe_allow_html=True)
