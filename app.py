import streamlit as st
import mysql.connector
import pandas as pd

# --- पेज का कॉन्फ़िगरेशन (टाइटल यहाँ बदला गया है) ---
st.set_page_config(page_title="KWR Plot Map", layout="wide")

# --- डेटाबेस कनेक्शन ---
@st.cache_resource(ttl=600)
def init_connection():
    try:
        # 20 सेकंड का कनेक्शन टाइमआउट जोड़ा गया है
        return mysql.connector.connect(**st.secrets["mysql"], connection_timeout=20)
    except mysql.connector.Error as e:
        # यह एरर अब तुरंत दिखेगा, जिससे पता चलेगा कि कनेक्शन में क्या दिक्कत है
        st.error(f"Database Connection Error: {e}. Please check your credentials and Hostinger's remote access settings.")
        return None

# --- डेटाबेस फंक्शन्स ---
@st.cache_data(ttl=60)
def get_all_plots():
    conn = init_connection()
    if conn and conn.is_connected():
        df = pd.read_sql("SELECT id, plot_number, status FROM plots ORDER BY plot_number;", conn)
        conn.close()
        return df
    return pd.DataFrame()

def run_query(query, params):
    conn = init_connection()
    if conn and conn.is_connected():
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
            st.cache_data.clear() # डेटा बदलने के बाद कैश क्लियर करें
        except mysql.connector.Error as e:
            st.error(f"Database Query Error: {e}")
        finally:
            conn.close()

# --- मुख्य ऐप का UI (मुख्य हेडिंग यहाँ बदली गई है) ---
st.title("KWR Plot Map By Aiclex Technologies")

# --- एडमिन लॉगइन (साइडबार में) ---
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
    if not plots_df.empty:
        plot_numbers = plots_df['plot_number'].tolist()
        plot_id_map = pd.Series(plots_df.id.values, index=plots_df.plot_number).to_dict()
    else:
        plot_numbers = []
        plot_id_map = {}

    # --- 1. स्टेटस अपडेट करें ---
    st.sidebar.subheader("Update Plot Status")
    selected_plot_update = st.sidebar.selectbox("Select Plot to Update", options=plot_numbers, key="update_select")
    statuses = ["Available", "Booked", "Sold"]
    new_status = st.sidebar.selectbox("Select New Status", options=statuses)
    if st.sidebar.button("Update Status"):
        if selected_plot_update:
            plot_id_to_update = plot_id_map[selected_plot_update]
            run_query("UPDATE plots SET status = %s WHERE id = %s", (new_status, plot_id_to_update))
            st.sidebar.success(f"Plot {selected_plot_update} updated to {new_status}!")
            st.experimental_rerun()

    # --- 2. नया प्लॉट जोड़ें ---
    st.sidebar.subheader("Add New Plot")
    new_plot_number = st.sidebar.number_input("Enter New Plot Number", min_value=1, step=1)
    initial_status = st.sidebar.selectbox("Initial Status", options=statuses, key="add_status")
    if st.sidebar.button("Add Plot"):
        if new_plot_number in plot_numbers:
            st.sidebar.error(f"Plot {new_plot_number} already exists!")
        else:
            run_query("INSERT INTO plots (plot_number, status) VALUES (%s, %s)", (new_plot_number, initial_status))
            st.sidebar.success(f"Plot {new_plot_number} added successfully!")
            st.experimental_rerun()

    # --- 3. प्लॉट डिलीट करें ---
    st.sidebar.subheader("Delete Plot")
    plot_to_delete = st.sidebar.selectbox("Select Plot to Delete", options=plot_numbers, key="delete_select")
    if st.sidebar.button("Delete Plot"):
        if plot_to_delete:
            plot_id_to_delete = plot_id_map[plot_to_delete]
            run_query("DELETE FROM plots WHERE id = %s", (plot_id_to_delete,))
            st.sidebar.warning(f"Plot {plot_to_delete} has been deleted.")
            st.experimental_rerun()

# --- प्लॉट्स को ग्रिड में दिखाएं ---
st.subheader("Current Plot Availability")
plots_df = get_all_plots()

if plots_df.empty and not st.session_state.get('logged_in', False):
    st.warning("Could not load plot data. Please try again later.")
else:
    STATUS_COLORS = {"Available": "#28a745", "Booked": "#ffc107", "Sold": "#dc3545"}
    cols_per_row = 10
    cols = st.columns(cols_per_row)
    for index, row in plots_df.iterrows():
        plot_number, status = row['plot_number'], row['status']
        color = STATUS_COLORS.get(status, "#6c757d")
        with cols[index % cols_per_row]:
            st.markdown(f"""
            <div style="background-color: {color}; padding: 20px; border-radius: 10px; color: white; text-align: center; font-size: 24px; font-weight: bold; margin: 10px 5px;">
                {plot_number}
            </div>
            """, unsafe_allow_html=True)
