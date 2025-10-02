import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# --- पेज का कॉन्फ़िगरेशन ---
st.set_page_config(page_title="KWR Plot Map", layout="wide")

# --- SQLAlchemy डेटाबेस कनेक्शन ---
@st.cache_resource(ttl=600)
def init_connection():
    try: # <-- यहाँ ':' जोड़ा गया है
        # secrets.toml से जानकारी लेकर एक कनेक्शन स्ट्रिंग बनाएं
        db_secrets = st.secrets["mysql"]
        db_uri = f"mysql+pymysql://{db_secrets['user']}:{db_secrets['password']}@{db_secrets['host']}:{db_secrets['port']}/{db_secrets['database']}"
        
        # SQLAlchemy इंजन बनाएं
        engine = create_engine(db_uri)
        return engine
    except Exception as e:
        st.error(f"Database Connection Error using SQLAlchemy: {e}")
        return None

# --- डेटाबेस फंक्शन्स ---
@st.cache_data(ttl=60)
def get_all_plots():
    engine = init_connection()
    if engine:
        try:
            # SQLAlchemy इंजन सीधे pandas के साथ काम करता है
            with engine.connect() as connection:
                df = pd.read_sql("SELECT id, plot_number, status FROM plots ORDER BY plot_number;", connection)
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
    if st.sidebar.button("Update Status"):
        if selected_plot_update:
            plot_id_to_update = plot_id_map[selected_plot_update]
            run_query("UPDATE plots SET status = :status WHERE id = :id", {'status': new_status, 'id': plot_id_to_update})
            st.sidebar.success(f"Plot {selected_plot_update} updated to {new_status}!")
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
    st.warning("Could not load plot data. Check connection or if plots exist.")
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
