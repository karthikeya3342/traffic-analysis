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
    kpi1, kpi2, kpi3 = st.columns(3)
    
    df = read_stats()
    
    if not df.empty:
        # Default Logic (Fallback)
        total_vehicles = df['vehicle_count'].iloc[-1]
        total_violations = df['violations'].sum() # Incorrect aggregate, but best effort without summary
        avg_density = df['vehicle_count'].mean()
        
        # Accurate Logic (if available)
        if os.path.exists(SUMMARY_FILE):
            try:
                with open(SUMMARY_FILE, "r") as f:
                    summary = json.load(f)
                    total_violations = summary.get("total_violations", total_violations)
                    # vehicle_count and density usually fine from CSV, but can update if needed
            except:
                pass

        kpi1.metric("Current Vehicles", int(total_vehicles))
        kpi2.metric("Total Violations", int(total_violations))
        kpi3.metric("Avg Density", f"{avg_density:.1f}")
        
        st.markdown("---")
        
        # Vehicle Classification Chart
        class_counts = summary.get("class_distribution", {})
        if class_counts:
             st.subheader("📊 Vehicle Classification")
             
             # Convert to lists for plotting
             labels = [k.title() for k in class_counts.keys()]
             sizes = list(class_counts.values())
             
             # Create Pie Chart
             fig1, ax1 = plt.subplots(figsize=(3, 3))
             # Use a dark-mode friendly style if possible, but default is okay with transparent bg
             wedges, texts, autotexts = ax1.pie(
                 sizes, 
                 labels=labels, 
                 autopct='%1.1f%%', 
                 startangle=90,
                 textprops={'color': "white"} # Assuming dark theme for better visibility
             )
             
             # Equal aspect ratio ensures that pie is drawn as a circle
             ax1.axis('equal')  
             
             # Transparent background
             fig1.patch.set_alpha(0)
             
             # Render
             c_pie, _ = st.columns([1, 2]) # Limit width
             with c_pie:
                st.pyplot(fig1, use_container_width=True)
             
             plt.close(fig1)
             
             st.markdown("---")

        # Breakdown Section (Side-by-Side)
        c_queue, c_log = st.columns([1, 1])
        
        # 1. Lane Queue Details (Left)
        with c_queue:
            st.markdown("### 🚙 Lane Queue Details (Final)")
            queue_stats = summary.get("queue_stats", {})
            if queue_stats:
                for lane_name, data in queue_stats.items():
                    count = data.get('count', 0)
                    progress_value = min(count / 20.0, 1.0)
                    
                    sub_c1, sub_c2 = st.columns([1, 2])
                    sub_c1.write(f"**{lane_name}**")
                    sub_c2.progress(progress_value, text=f"{count} veh")
            else:
                st.info("No queue data.")

        # 2. Violation Log History (Right)
        with c_log:
            recent_violations = summary.get("recent_violations", [])
            if recent_violations:
                st.markdown("### 📜 Violation Log History")
                df_log = pd.DataFrame(recent_violations)
                df_log = df_log[["time", "type", "vehicle_id"]]
                df_log.columns = ["Time", "Type", "Vehicle ID"]
                
                # Show top 10 rows by default
                st.dataframe(df_log.head(10), use_container_width=True)
                
                # Expander for full list
                with st.expander("View Full Log", expanded=False):
                    st.dataframe(df_log, use_container_width=True)
                    st.caption(f"Total entries: {len(df_log)}")
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
                    use_container_width=True
                )
            else:
                st.button("Stats CSV Not Available", disabled=True, use_container_width=True)

        with ec2:
            if os.path.exists(SUMMARY_FILE):
                with open(SUMMARY_FILE, "r") as f:
                    json_data = f.read()
                st.download_button(
                    label="Download Summary Report (JSON)",
                    data=json_data,
                    file_name="traffic_summary.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                 st.button("Summary JSON Not Available", disabled=True, use_container_width=True)

    else:
        st.warning("No stats available yet. Run analysis from the sidebar.")

def render_video_output(video_path):
    st.subheader("Processed Video Output")
    if os.path.exists(video_path):
        try:
            # Bust cache using mtime as key
            t = os.path.getmtime(video_path)
            st.video(video_path, key=f"video_{t}")
        except Exception as e:
            st.warning(f"Video reload warning: {e}")
            st.video(video_path) # Fallback without key
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
                 
                 fig_live, ax_live = plt.subplots(figsize=(3, 3))
                 ax_live.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                             textprops={'color': "white"})
                 ax_live.axis('equal')
                 fig_live.patch.set_alpha(0)
                 
                 # Render
                 c_p1, _ = st.columns([1, 2])
                 with c_p1:
                     st.pyplot(fig_live, use_container_width=True)
                 plt.close(fig_live)
            else:
                 st.info("Waiting for classification data...")

