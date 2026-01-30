import streamlit as st
import glob
import yaml

# UI Components
from src.ui.patch import apply_streamlit_patch
from src.ui.lane_config import render_lane_config
from src.ui.process_manager import render_analysis_control
from src.ui.dashboard_components import render_metrics, render_video_output

# Apply patch immediately
apply_streamlit_patch()

st.set_page_config(page_title="Traffic Analytics Dashboard", layout="wide")

# Load Config
def load_config():
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)

def save_config(config):
    with open("config/config.yaml", "w") as f:
        yaml.dump(config, f)

def main():
    config = load_config()
    st.title("🚦 Intelligent Traffic Analysis & Violation Detection")

    # --- Sidebar ---
    st.sidebar.header("Control Panel")

    # Video Selection
    video_files = glob.glob("data/*.mp4")
    selected_video = st.sidebar.selectbox("Select Input Video", video_files, index=0 if video_files else None)
    
    # Store selected video in config if needed, or just use for analysis
    if selected_video and selected_video != config['video']['source']:
        # Optional: update config in memory or valid for session
        pass

    # --- Lane Configuration ---
    # This component handles drawing and updating config['analytics']['lanes'] internally
    # It reads/writes directly to config.yaml via its own logic, or we could pass a callback.
    # For now, it shares the storage method.
    render_lane_config(config, selected_video)

    # --- Analysis Control ---
    render_analysis_control(selected_video, config)

    st.sidebar.markdown("---")
    st.sidebar.info(f"Model: {config['detection']['model']}")

    # --- Main Content ---
    render_metrics(config)
    
    render_video_output(config['video']['output'])

if __name__ == "__main__":
    main()
