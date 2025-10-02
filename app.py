import streamlit as st
import mysql.connector # psycopg2 की जगह mysql.connector इम्पोर्ट करें
import pandas as pd

# --- पेज का कॉन्फ़िगरेशन ---
st.set_page_config(page_title="Plot Status Dashboard", layout="wide")

# --- डेटाबेस कनेक्शन ---
@st.cache_resource
def init_connection():
    try:
        # [mysql] सीक्रेट्स का उपयोग करें
        return mysql.connector.connect(**st.secrets["mysql"])
    except mysql.connector.Error as e:
        st.error(f"Error connecting to MySQL database: {e}")
        return None

# --- डेटाबेस फंक्शन्स ---
@st.cache_data(ttl=60)
def get_all_plots():
    conn = init_connection()
    if conn:
        df = pd.read_sql("SELECT id, plot_number, status FROM plots ORDER BY plot_number;", conn)
        return df
    return pd.DataFrame()

def update_plot_status(plot_id, status):
    conn = init_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                # MySQL के लिए भी %s प्लेसहोल्डर काम करता है
                cur.execute("UPDATE plots SET status = %s WHERE id = %s", (status, plot_id))
                conn.commit()
            st.cache_data.clear()
        except mysql.connector.Error as e:
            st.error(f"Error updating data: {e}")
            conn.rollback() # अगर एरर आए तो बदलाव वापस ले लें

# --- मुख्य ऐप का UI ---
st.title("🏡 Real Estate Plot Status Dashboard")

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
    st.sidebar.subheader("Update Plot Status")
    plots_df = get_all_plots()
    if not plots_df.empty:
        plot_id_map = pd.Series(plots_df.id.values, index=plots_df.plot_number).to_dict()
        plot_numbers = plots_df['plot_number'].tolist()
        selected_plot_number = st.sidebar.selectbox("Select Plot Number", options=plot_numbers)
        statuses = ["Available", "Booked", "Sold"]
        new_status = st.sidebar.selectbox("Select New Status", options=statuses)

        if st.sidebar.button("Update Status"):
            plot_id_to_update = plot_id_map[selected_plot_number]
            update_plot_status(plot_id_to_update, new_status)
            st.sidebar.success(f"Plot {selected_plot_number} status updated to {new_status}!")
            st.experimental_rerun()

# --- प्लॉट्स को ग्रिड में दिखाएं ---
st.subheader("Current Plot Availability")
plots_df = get_all_plots()

if plots_df.empty:
    st.warning("Could not load plot data.")
else:
    STATUS_COLORS = {
        "Available": "#28a745", "Booked": "#ffc107", "Sold": "#dc3545"
    }
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
