import streamlit as st
import sqlite3
import requests
import pandas as pd
import datetime

st.set_page_config(page_title="IntentLock Enterprise Dashboard", page_icon="🛡️", layout="wide")

DB_FILE = "intentlock_ollama.db"
BASE_URL = "http://127.0.0.1:8000"

st.title("🛡️ IntentLock Enterprise: AI Guardrail & Time-Travel Control Plane")
st.markdown("Autonomous AI-driven governance, snapshot history, and instant self-healing rollback gateway.")

# Sidebar for Quick Intent Execution
st.sidebar.header("🚀 Trigger Deployment Intent")
agent_input = st.sidebar.text_input("Agent / Developer", "DevOpsLead")
service_input = st.sidebar.text_input("Target Service", "payment-api")
action_input = st.sidebar.text_area("Configuration Action", "deploy stable v2.1 ingress service")

if st.sidebar.button("Send Intent to Proxy"):
    try:
        payload = {
            "agent_name": agent_input,
            "target_service": service_input,
            "config_action": action_input
        }
        res = requests.post(f"{BASE_URL}/apply", json=payload)
        data = res.json()
        if data.get("status") in ["approved_and_deployed"]:
            st.sidebar.success(f"Success: {data.get('message')}")
        elif data.get("status") in ["rolled_back", "auto_rolled_back"]:
            st.sidebar.error(f"Blocked/Rolled Back: {data.get('error') or data.get('reason')}")
        else:
            st.sidebar.json(data)
    except Exception as e:
        st.sidebar.error(f"Connection Error: Is FastAPI running on port 8000? ({e})")

# Fetch Database Snapshots
def load_snapshots():
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql("SELECT * FROM snapshots ORDER BY id DESC", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=["id", "timestamp", "state"])

df_snapshots = load_snapshots()

# Main Dashboard Metrics
col1, col2, col3 = st.columns(3)
with col1:
    total_snaps = len(df_snapshots)
    st.metric("Total System Snapshots", total_snaps)
with col2:
    latest_id = df_snapshots["id"].iloc[0] if not df_snapshots.empty else 0
    st.metric("Latest Active Snapshot ID", latest_id)
with col3:
    st.metric("Guardrail Engine", "Ollama (Llama 3) Active")

st.divider()

# History & Time-Travel Section
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📜 Snapshot & State History (Time-Travel Ledger)")
    if not df_snapshots.empty:
        df_display = df_snapshots.copy()
        df_display["timestamp"] = df_display["timestamp"].apply(lambda x: datetime.datetime.fromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S'))
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No snapshots recorded yet. Run an intent via sidebar.")

with col_right:
    st.subheader("🔄 Time-Travel Rollback")
    st.markdown("Restore cluster state to any historical snapshot ID instantly.")
    
    target_snap_id = st.number_input("Select Target Snapshot ID", min_value=1, step=1, value=int(latest_id) if not df_snapshots.empty else 1)
    
    if st.button("Execute Time-Travel Rollback", type="primary"):
        try:
            res = requests.post(f"{BASE_URL}/rollback/{target_snap_id}")
            if res.status_code == 200:
                st.success(f"Successfully rolled back to Snapshot ID [{target_snap_id}]!")
                st.json(res.json())
                st.rerun()
            else:
                st.error(f"Error: {res.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"Failed to connect to gateway: {e}")

# Current Cluster State Viewer
st.divider()
st.subheader("🌐 Live Cluster State View")
if not df_snapshots.empty:
    latest_state = df_snapshots["state"].iloc[0]
    try:
        parsed_state = eval(latest_state)
        if isinstance(parsed_state, dict):
            st.json(parsed_state)
        else:
            st.write(latest_state)
    except Exception:
        st.write(latest_state)
else:
    st.write("No state data available.")
