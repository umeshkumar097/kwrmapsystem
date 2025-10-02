import streamlit as st
import psycopg2
import pandas as pd

# --- पेज कॉन्फ़िगरेशन ---
st.set_page_config(page_title="Plot Status Dashboard", layout="wide")

# --- डेटाबेस कनेक्शन ---
# st.cache_resource का उपयोग करके कनेक्शन को कैश करें ताकि ऐप बार-बार कनेक्ट न हो
@st.cache_resource
def init_connection():
    try:
        return psycopg2.connect(**st.secrets["postgres"])
    except psycopg2.OperationalError as e:
        st.error(f"Error connecting to database: {e}")
        return None

# --- डेटाबेस से डेटा लाने और अपडेट करने के लिए फंक्शन्स ---
@st.cache_data(ttl=60) # डेटा को 60 सेकंड के लिए कैश करें
def get_all_plots():
    conn = init_connection()
    if conn:
        df = pd.read_sql("SELECT id, plot_number, status FROM plots ORDER BY plot_number;", conn)
        return df
    return pd.DataFrame()

def update_plot_status(plot_id, status):
    conn = init_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE plots SET status = %s WHERE id = %s", (status, plot_id))
            conn.commit()

# --- मुख्य ऐप ---
st.title("🏡 Real Estate Plot Status Dashboard")

# --- एडमिन लॉगइन (साइडबार में) ---
st.sidebar.header("🔑 Admin Panel")
password = st.sidebar.text_input("Enter Password", type="password")

# पासवर्ड की जाँच करें
if password == st.secrets["admin"]["password"]:
    st.session_state['logged_in'] = True
    st.sidebar.success("✅ Logged in successfully!")
elif password: # अगर कुछ लिखा है लेकिन गलत है
    st.sidebar.error("❌ Incorrect password.")
    st.session_state.pop('logged_in', None)

# --- एडमिन कंट्रोल (अगर लॉग इन है तो दिखाएं) ---
if st.session_state.get('logged_in', False):
    st.sidebar.subheader("Update Plot Status")
    
    plots_df = get_all_plots()
    if not plots_df.empty:
        plot_numbers = plots_df['plot_number'].tolist()
        
        # प्लॉट नंबर को id से मैप करें
        plot_id_map = {row['plot_number']: row['id'] for index, row in plots_df.iterrows()}

        selected_plot_number = st.sidebar.selectbox("Select Plot Number", options=plot_numbers)
        
        statuses = ["Available", "Booked", "Sold"]
        new_status = st.sidebar.selectbox("Select New Status", options=statuses)

        if st.sidebar.button("Update Status"):
            plot_id_to_update = plot_id_map[selected_plot_number]
            update_plot_status(plot_id_to_update, new_status)
            st.cache_data.clear() # अपडेट के बाद कैश क्लियर करें
            st.sidebar.success(f"Plot {selected_plot_number} status updated to {new_status}!")
            st.experimental_rerun() # पेज को तुरंत री-रन करें ताकि बदलाव दिखे

# --- सभी प्लॉट्स को ग्रिड में दिखाएं ---
st.subheader("Current Plot Availability")
plots_df = get_all_plots()

if plots_df.empty:
    st.warning("No plots found in the database. Please check the database connection and setup.")
else:
    # स्टेटस के लिए रंग
    STATUS_COLORS = {
        "Available": "#28a745", # हरा
        "Booked": "#ffc107",   # पीला
        "Sold": "#dc3545"      # लाल
    }

    # एक पंक्ति में कितने कॉलम दिखाने हैं
    cols_per_row = 10
    cols = st.columns(cols_per_row)
    for index, row in plots_df.iterrows():
        plot_number = row['plot_number']
        status = row['status']
        color = STATUS_COLORS.get(status, "#6c757d") # अगर कोई और स्टेटस हो तो ग्रे
        
        # हर प्लॉट के लिए एक रंगीन बॉक्स बनाएं
        with cols[index % cols_per_row]:
            st.markdown(f"""
            <div style="background-color: {color}; padding: 20px; border-radius: 10px; color: white; text-align: center; font-size: 24px; font-weight: bold; margin: 10px 5px;">
                {plot_number}
            </div>
            """, unsafe_allow_html=True)
