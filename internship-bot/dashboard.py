import streamlit as st
import pandas as pd
from pathlib import Path
import os
import plotly.express as px

# --- Page Config ---
st.set_page_config(
    page_title="Internship Bot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS for Aesthetics ---
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    h1, h2, h3 {
        color: #00ffcc;
        font-family: 'Inter', sans-serif;
    }
    .metric-card {
        background-color: #1e2530;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        text-align: center;
        border-left: 5px solid #00ffcc;
    }
    .metric-value {
        font-size: 36px;
        font-weight: bold;
        color: white;
    }
    .metric-label {
        color: #a0aab2;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "logs" / "applications.csv"

@st.cache_data(ttl=60) # Refresh data every minute
def load_data():
    if not CSV_PATH.exists():
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(CSV_PATH)
        # Ensure we have the right columns even if the file is empty or malformed
        expected_cols = ["Date", "Company", "Role", "Location", "Source", "Status", "Score", "Apply URL", "Cover Note Preview"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = ""
        
        # Sort by most recent
        df = df.sort_values(by="Date", ascending=False).reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

# --- Sidebar ---
st.sidebar.title("🤖 Internship Bot")
st.sidebar.markdown("Automated scouting & applying.")

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("▶️ Run Bot Now (Dry Run)"):
    import subprocess
    st.sidebar.info("Starting bot in background...")
    subprocess.Popen(["python", "main.py", "--run-now", "--dry-run"], cwd=str(BASE_DIR))

st.sidebar.markdown("---")
st.sidebar.subheader("Filter Results")

if not df.empty:
    sources = ["All"] + list(df["Source"].dropna().unique())
    selected_source = st.sidebar.selectbox("Filter by Source", sources)

    statuses = ["All"] + list(df["Status"].dropna().unique())
    selected_status = st.sidebar.selectbox("Filter by Status", statuses)
else:
    selected_source = "All"
    selected_status = "All"

# --- Main Dashboard ---
st.title("🚀 Automated Applications Dashboard")
st.markdown("Track the internships your bot has found and applied to.")

if df.empty:
    st.info("Waiting for the bot to log its first applications... Check back in a few minutes once the bot finishes running!")
    st.stop()

# Filter data
filtered_df = df.copy()
if selected_source != "All":
    filtered_df = filtered_df[filtered_df["Source"] == selected_source]
if selected_status != "All":
    filtered_df = filtered_df[filtered_df["Status"] == selected_status]

# --- Metrics ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(df)}</div>
        <div class="metric-label">Total Logs</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    applied_count = len(df[df["Status"].astype(str).str.contains("Applied|Pending", case=False, na=False)])
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #00ccff;">
        <div class="metric-value">{applied_count}</div>
        <div class="metric-label">Successful Applications</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    skipped_count = len(df[df["Status"].astype(str).str.contains("Skipped", case=False, na=False)])
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #ff9900;">
        <div class="metric-value">{skipped_count}</div>
        <div class="metric-label">Skipped (Duplicate/Low Score)</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    error_count = len(df[df["Status"].astype(str).str.contains("Error", case=False, na=False)])
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #ff3333;">
        <div class="metric-value">{error_count}</div>
        <div class="metric-label">Application Errors</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Success Rate Chart ---
if not filtered_df.empty:
    st.subheader("📊 Application Success Rate")
    status_counts = filtered_df["Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    fig = px.pie(status_counts, values="Count", names="Status", hole=0.4,
                 color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Data Table ---
st.subheader(f"📋 Application Log ({len(filtered_df)} items)")

# Make the dataframe look nicer in the UI
display_df = filtered_df.copy()

# Make URLs clickable if they exist
if "Apply URL" in display_df.columns:
    display_df["Apply URL"] = display_df["Apply URL"].apply(
        lambda x: f'<a href="{x}" target="_blank">View Job</a>' if pd.notna(x) and str(x).startswith('http') else x
    )

st.write(
    display_df.to_html(escape=False, index=False), 
    unsafe_allow_html=True
)

st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption("Dashboard auto-refreshes every 60 seconds. Powered by Streamlit & your custom Python Bot.")
