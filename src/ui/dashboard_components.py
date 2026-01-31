import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import json

STATS_FILE = "data/stats.csv"
SUMMARY_FILE = "data/final_summary.json"

def read_stats():
    if os.path.exists(STATS_FILE):
        try:
            # Explicitly check for empty file to avoid pandas error
            if os.path.getsize(STATS_FILE) == 0:
                return pd.DataFrame()
            return pd.read_csv(STATS_FILE)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def render_metrics(config):
    """
    Renders KPIs and Charts based on stats.csv and final_summary.json
    """
    df = read_stats()
    
    if not df.empty:
        # Downsample graphs to show every 30th frame as requested
        # Only apply if we have enough data to make a graph
        if len(df) > 30:
            df = df.iloc[::30, :]
            
        # Load summary for classification/logs
        summary = {}
        if os.path.exists(SUMMARY_FILE):
            try:
                with open(SUMMARY_FILE, "r") as f: summary = json.load(f)
            except: pass

        # --- GRAPHS SECTION (Replacing KPIs) ---
        st.subheader("📈 Analysis Trends")
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**🚗 Vehicles / Time**")
            st.line_chart(df, x='frame', y='vehicle_count', height=250)
        with g2:
            st.markdown("**🚦 Queue Density Trend**")
            d_cols = [c for c in df.columns if '_density' in c]
            if d_cols:
                st.line_chart(df, x='frame', y=d_cols, height=250)
            else:
                 # Fallback to counts if density missing
                 c_cols = [c for c in df.columns if '_count' in c]
                 st.line_chart(df, x='frame', y=c_cols, height=250)
        
        st.markdown("---")
        
        # --- CLASSIFICATION & LOGS ---
        c_pie, c_log = st.columns([1, 1])
        
        with c_pie:
             st.subheader("📊 Vehicle Classification")
             class_counts = summary.get("class_distribution", {})
             if class_counts:
                 # Pie Chart Logic
                 labels = [k.title() for k in class_counts.keys()]
                 sizes = list(class_counts.values())
                 fig1, ax1 = plt.subplots(figsize=(2, 2))
                 ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'color': "white", 'fontsize': 8})
                 ax1.axis('equal')
                 fig1.patch.set_alpha(0)
                 
                 # Constrain width
                 sub_c, _ = st.columns([2, 3])
                 with sub_c:
                     st.pyplot(fig1, width="stretch")
                 plt.close(fig1)
             else:
                 st.info("No classification data.")

        with c_log:
             st.subheader("📜 Violation Log")
             recent = summary.get("recent_violations", [])
             if recent:
                  df_log = pd.DataFrame(recent)
                  if not df_log.empty:
                      df_log = df_log[["time", "type", "vehicle_id"]]
                      df_log.columns = ["Time", "Type", "ID"]
                      st.dataframe(df_log, height=250, width="stretch")
             else:
                  st.info("No violations recorded.")
        
        st.markdown("---")
        
        # --- Data Export Section ---
        st.subheader("📥 Export Analysis Data")
        ec1, ec2 = st.columns(2)
        
        with ec1:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, "r") as f:
                    csv_data = f.read()
                st.download_button(
                    label="Download Complete Stats (CSV)",
                    data=csv_data,
                    file_name="traffic_analysis_stats.csv",
                    mime="text/csv",
                    width="stretch"
                )
            else:
                st.button("Stats CSV Not Available", disabled=True, width="stretch")

        with ec2:
            if os.path.exists(SUMMARY_FILE):
                with open(SUMMARY_FILE, "r") as f:
                    json_data = f.read()
                st.download_button(
                    label="Download Summary Report (JSON)",
                    data=json_data,
                    file_name="traffic_summary.json",
                    mime="application/json",
                    width="stretch"
                )
            else:
                 st.button("Summary JSON Not Available", disabled=True, width="stretch")

    else:
        st.warning("No stats available yet. Run analysis from the sidebar.")

def render_video_output(video_path):
    st.subheader("Processed Video Output")
    
    if os.path.exists(video_path):
        st.video(video_path)
    else:
        st.info("Waiting for processed video output...")

# --- Near-Real-Time Dashboard Components ---

def init_live_dashboard():
    """
    Creates the layout for the live dashboard and returns placeholders.
    """
    st.subheader("Live Analysis Monitor")
    
    # 1. KPI Container
    ph_kpi_container = st.empty()
    
    # Initialize KPIs with empty state
    with ph_kpi_container.container():
        k1, k2, k3 = st.columns(3)
        k1.metric("🚗 Vehicle Count", "0")
        k2.metric("🚨 Total Violations", "0")
        k3.metric("🚦 Avg Queue Density", "0.0")

    st.markdown("---")
    
    # 2. Charts and Logs Area
    c1, c2 = st.columns([1, 1])
    
    with c1:
        ph_queue_chart = st.empty()
        # Default content
        ph_queue_chart.info("Waiting for queue data...")
        
        st.markdown("---")
        ph_class_chart = st.empty()
        ph_class_chart.info("Waiting for classification...")
        
    with c2:
        ph_violations_table = st.empty()
        # Default content
        ph_violations_table.info("Waiting for violation logs...")
        
    return {
        "kpi_container": ph_kpi_container,
        "queue_chart": ph_queue_chart,
        "class_chart": ph_class_chart,
        "violations": ph_violations_table
    }

def update_live_dashboard(placeholders: dict, stats: dict):
    """
    Updates the dashboard placeholders with fresh data from live_stats.json.
    """
    # 1. Top Level KPIs
    with placeholders["kpi_container"].container():
        k1, k2, k3 = st.columns(3)
        k1.metric("🚗 Vehicle Count", stats.get("vehicle_count", 0))
        k2.metric("🚨 Total Violations", stats.get("total_violations", 0))
        k3.metric("🚦 Avg Queue Density", f"{stats.get('density', 0):.1f}")
    
    # 2. Queue Analytics (Visual Bars)
    with placeholders["queue_chart"].container():
        st.markdown("### 🚙 Live Queue Status")
        queue_stats = stats.get("queue_stats", {})
        
        if queue_stats:
            for lane_name, data in queue_stats.items():
                count = data.get('count', 0)
                # status = data.get('status', 'Low') # Not used in this display
                
                # 20 is arbitrary max for visualization
                progress_value = min(count / 20.0, 1.0)
                
                # Use columns for layout
                c1, c2 = st.columns([1, 3])
                c1.caption(f"**{lane_name}** ({count} veh)")
                c2.progress(progress_value)
        else:
            st.info("No lane queue data available yet.")
            
    # 3. Recent Violations Table
    with placeholders["violations"].container():
        st.markdown("### 📝 Recent Violations Log")
        recent = stats.get("recent_violations", [])
        
        if recent:
            # Create simple table
            df = pd.DataFrame(recent)
            # Reorder columns explicitly to match headers
            # Keys in dict: 'time', 'vehicle_id', 'type'
            df = df[["time", "type", "vehicle_id"]]
            df.columns = ["Time", "Type", "Vehicle ID"]
            st.table(df.head(5)) 
            
            # Expander for full list
            with st.expander("View Full Log", expanded=False):
                st.dataframe(df, use_container_width=True)
                st.caption(f"Total entries: {len(df)}")
        else:
            st.info("No violations detected yet.")

    # 4. Vehicle Classification (Live Pie Chart) - Append to Queue Chart area (C1) usually, 
    # but we can render it into its own placeholder if passed, or reuse c1 logic.
    # Let's assume 'class_chart' placeholder is added to the dict.
    if "class_chart" in placeholders:
        with placeholders["class_chart"].container():
            st.markdown("### 📊 Class Distribution")
            class_counts = stats.get("class_distribution", {})
            if class_counts:
                 # Create Pie Chart
                 labels = [k.title() for k in class_counts.keys()]
                 sizes = list(class_counts.values())
                 
                 fig_live, ax_live = plt.subplots(figsize=(2, 2))
                 ax_live.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                             textprops={'color': "white", 'fontsize': 8})
                 ax_live.axis('equal')
                 fig_live.patch.set_alpha(0)
                 
                 # Render
                 c_p1, _ = st.columns([1, 2])
                 with c_p1:
                     st.pyplot(fig_live, width="stretch")
                 plt.close(fig_live)
            else:
                 st.info("Waiting for classification data...")

