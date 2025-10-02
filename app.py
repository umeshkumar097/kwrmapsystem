import streamlit as st
import psycopg2
import pandas as pd

# --- पेज का कॉन्फ़िगरेशन (सबसे पहली कमांड होनी चाहिए) ---
st.set_page_config(page_title="Plot Status Dashboard", layout="wide")

# --- डेटाबेस कनेक्शन ---
# st.cache_resource का उपयोग करके कनेक्शन को कैश करें ताकि ऐप बार-बार कनेक्ट न हो
@st.cache_resource
def init_connection():
    """
    Connects to the PostgreSQL database using credentials from st.secrets.
    Returns the connection object.
    """
    try:
        return psycopg2.connect(**st.secrets["postgres"])
    except psycopg2.OperationalError as e:
        st.error(f"Error: Could not connect to the database. Please check your secrets.toml file. Details: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during connection: {e}")
        return None

# --- डेटाबेस से डेटा लाने और अपडेट करने के लिए फंक्शन्स ---
# st.cache_data का उपयोग करके डेटा को कैश करें ताकि बार-बार डेटाबेस से न पूछना पड़े
@st.cache_data(ttl=60) # डेटा को 60 सेकंड के लिए कैश करें
def get_all_plots():
    """
    Fetches all plot data from the database and returns it as a Pandas DataFrame.
    """
    conn = init_connection()
    if conn:
        try:
            df = pd.read_sql("SELECT id, plot_number, status FROM plots ORDER BY plot_number;", conn)
            return df
        except Exception as e:
            st.error(f"Error fetching data from the database: {e}")
    return pd.DataFrame() # अगर कोई एरर हो तो खाली DataFrame भेजें

def update_plot_status(plot_id, status):
    """
    Updates the status of a specific plot in the database.
    """
    conn = init_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE plots SET status = %s WHERE id = %s", (status, plot_id))
                conn.commit()
            # अपडेट के बाद कैश क्लियर करें ताकि बदलाव तुरंत दिखे
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Error updating data: {e}")


# --- मुख्य ऐप का UI और लॉजिक ---

st.title("🏡 Real Estate Plot Status Dashboard")

# --- एडमिन लॉगइन (साइडबार में) ---
st.sidebar.header("🔑 Admin Panel")
password = st.sidebar.text_input("Enter Admin Password", type="password")

# पासवर्ड की जाँच करें
if password == st.secrets["admin"]["password"]:
    st.session_state['logged_in'] = True
    st.sidebar.success("✅ Logged in successfully!")
elif password: # अगर कुछ लिखा है लेकिन गलत है
    st.sidebar.error("❌ Incorrect password.")
    # अगर गलत पासवर्ड डाला है तो लॉगआउट कर दें
    if 'logged_in' in st.session_state:
        del st.session_state['logged_in']

# --- एडमिन कंट्रोल (अगर लॉग इन है तो दिखाएं) ---
if st.session_state.get('logged_in', False):
    st.sidebar.subheader("Update Plot Status")
    
    plots_df = get_all_plots()
    if not plots_df.empty:
        # प्लॉट नंबर को id से मैप करें ताकि अपडेट करना आसान हो
        plot_id_map = pd.Series(plots_df.id.values, index=plots_df.plot_number).to_dict()

        plot_numbers = plots_df['plot_number'].tolist()
        selected_plot_number = st.sidebar.selectbox("Select Plot Number", options=plot_numbers)
        
        statuses = ["Available", "Booked", "Sold"]
        new_status = st.sidebar.selectbox("Select New Status", options=statuses)

        if st.sidebar.button("Update Status"):
            plot_id_to_update = plot_id_map[selected_plot_number]
            update_plot_status(plot_id_to_update, new_status)
            st.sidebar.success(f"Plot {selected_plot_number} status updated to {new_status}!")
            # पेज को तुरंत री-रन करें ताकि बदलाव दिखे
            st.experimental_rerun()

# --- सभी प्लॉट्स को ग्रिड में दिखाएं ---
st.subheader("Current Plot Availability")
plots_df = get_all_plots()

if plots_df.empty:
    st.warning("Could not load plot data. Please check the database connection and ensure the 'plots' table exists.")
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
