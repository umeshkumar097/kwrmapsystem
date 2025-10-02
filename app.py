import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# --- पेज का कॉन्फ़िगरेशन ---
st.set_page_config(page_title="KWR Plot Map", layout="wide")

# --- Responsive Grid के लिए CSS ---
# यह CSS सुनिश्चित करेगा कि ग्रिड सभी डिवाइस पर अच्छा दिखे
st.markdown("""
<style>
.plot-grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
    gap: 15px;
    padding: 10px;
}
.plot-box {
    padding: 20px 5px; /* ऊपर-नीचे ज़्यादा, दाएं-बाएं कम padding */
    border-radius: 10px;
    color: white;
    text-align: center;
    font-size: 24px;
    font-weight: bold;
    cursor: pointer;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    transition: transform 0.2s;
}
.plot-box:hover {
    transform: scale(1.05); /* Hover पर थोड़ा बड़ा दिखेगा */
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
st.title("KWR Plot Map By Aiclex Technologies")

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

# --- एडमिन कंट्रोल ---
if st.session_state.get('logged_in', False):
    plots_df = get_all_plots()
    plot_numbers = plots_df['plot_number'].tolist() if not plots_df.empty else []
    plot_id_map = pd.Series(plots_df.id.values, index=plots_df.plot_number).to_dict() if not plots_df.empty else {}

    # 1. स्टेटस अपडेट करें
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

    # 2. नया प्लॉट जोड़ें
    st.sidebar.subheader("Add New Plot")
    new_plot_number = st.sidebar.number_input("Enter New Plot Number", min_value=1, step=1)
    initial_status = st.sidebar.selectbox("Initial Status", options=statuses, key="add_status")
    if st.sidebar.button("Add Plot"):
        if new_plot_number in plot_numbers:
            st.sidebar.error(f"Plot {new_plot_number} already exists!")
        else:
            run_query("INSERT INTO plots (plot_number, status) VALUES (:plot, :status)", {'plot': new_plot_number, 'status': initial_status})
            st.sidebar.success(f"Plot {new_plot_number} added successfully!")
            st.rerun()

    # 3. प्लॉट डिलीट करें
    st.sidebar.subheader("Delete Plot")
    plot_to_delete = st.sidebar.selectbox("Select Plot to Delete", options=plot_numbers, key="delete_select")
    if st.sidebar.button("Delete Plot"):
        if plot_to_delete:
            plot_id_to_delete = plot_id_map[plot_to_delete]
            run_query("DELETE FROM plots WHERE id = :id", {'id': plot_id_to_delete})
            st.sidebar.warning(f"Plot {plot_to_delete} has been deleted.")
            st.rerun()

# --- प्लॉट्स को ग्रिड में दिखाएं ---
st.subheader("Current Plot Availability")
plots_df = get_all_plots()

if plots_df.empty and not st.session_state.get('logged_in', False):
    st.warning("Could not load plot data.")
else:
    STATUS_COLORS = {"Available": "#28a745", "Booked": "#ffc107", "Sold": "#dc3545"}
    
    # सभी प्लॉट्स के लिए एक ही बार में HTML स्ट्रिंग बनाएं
    html_plots = []
    for index, row in plots_df.iterrows():
        plot_number, status = row['plot_number'], row['status']
        color = STATUS_COLORS.get(status, "#6c757d")
        
        # Tooltip के लिए टेक्स्ट
        tooltip_text = ""
        if status in ["Booked", "Sold"]:
            c_name = row['customer_name'] or ""
            co_name = row['company_name'] or ""
            details = []
            if c_name: details.append(f"Name: {c_name}")
            if co_name: details.append(f"Company: {co_name}")
            tooltip_text = "\n".join(details)
            if not tooltip_text: tooltip_text = f"Status: {status}"

        # हर एक प्लॉट के लिए HTML बनाएं
        html_plots.append(f'<div class="plot-box" style="background-color: {color};" title="{tooltip_text}">{plot_number}</div>')

    # पूरे ग्रिड को एक साथ रेंडर करें
    st.markdown(f'<div class="plot-grid-container">{"".join(html_plots)}</div>', unsafe_allow_html=True)
