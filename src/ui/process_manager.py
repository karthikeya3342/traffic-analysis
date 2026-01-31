import streamlit as st
import subprocess
import time
import json
import os
import pandas as pd
import sys
from src.ui.dashboard_components import init_live_dashboard, update_live_dashboard

def stop_running_process():
    """Forces the analysis process to stop."""
    process = st.session_state.get('process_handle')
    if process:
        # 1. Send polite signal first
        with open("data/.stop_signal", "w") as f: 
            f.write("stop")
        
        # 2. Give it a moment, then kill
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.kill() # Force kill if terminate fails
        except Exception:
            pass
            
        st.session_state['process_handle'] = None
    
    st.session_state['analyzing'] = False
    
    # Cleanup signal file
    if os.path.exists("data/.stop_signal"):
        try: os.remove("data/.stop_signal")
        except: pass

def render_analysis_control(selected_video, config):
    """
    Renders the analysis control (Run/Stop) and handles the process via session state.
    """
    # --- Analysis Control ---
    if 'analyzing' not in st.session_state:
        st.session_state['analyzing'] = False

    # Cleanup Zombies: If state says NOT analyzing, but handle exists -> KILL
    if not st.session_state['analyzing'] and st.session_state.get('process_handle'):
        stop_running_process()

    if st.sidebar.button("Run Analysis"):
        if selected_video:
            st.session_state['analyzing'] = True
        else:
            st.sidebar.warning("Please select a video first.")

    if st.sidebar.button("Stop Analysis"):
        stop_running_process()
        st.rerun()

    if st.session_state['analyzing']:
        st.sidebar.info("Analysis Running... Press 'Stop Analysis' to cancel.")
        
        # --- Signal Control ---
        st.sidebar.markdown("### 🚦 Signal Control")
        col1, col2 = st.sidebar.columns(2)
        
        if col1.button("🔴 RED", use_container_width=True):
            with open("data/signal_state.txt", "w") as f:
                f.write("RED")
                
        if col2.button("🟢 GREEN", use_container_width=True):
            with open("data/signal_state.txt", "w") as f:
                f.write("GREEN")
        
        # Show current state
        current_signal = "UNKNOWN"
        if os.path.exists("data/signal_state.txt"):
            with open("data/signal_state.txt", "r") as f:
                current_signal = f.read().strip()
        
        if current_signal == "RED":
            st.sidebar.error(f"Signal is {current_signal}")
        else:
            st.sidebar.success(f"Signal is {current_signal}")
        # ----------------------
        
        status_placeholder = st.sidebar.empty()
        log_placeholder = st.sidebar.empty()
        
        # Initialize Near-Real-Time Dashboard
        dashboard_placeholders = init_live_dashboard()
        
        # Clean up stop signal if exists
        if os.path.exists("data/.stop_signal"):
            try: os.remove("data/.stop_signal")
            except: pass

        # Persistence for process across reruns
        process = st.session_state.get('process_handle')
        log_file = "data/app.log"
        
        # UI Placeholders
        video_placeholder = st.empty() # For Live Video
        
        try:
            # START NEW PROCESS if needed
            if process is None or process.poll() is not None:
                status_placeholder.text("Starting process...")
                
                # Generate unique output filename to bust cache
                unique_output = f"data/output_{int(time.time())}.mp4"
                st.session_state['current_output_video'] = unique_output
                
                # Open log file
                f_log = open(log_file, "w") # Overwrite for new run
                
                process = subprocess.Popen(
                    [sys.executable, "main.py", "--source", selected_video, "--output", unique_output],
                    stdout=f_log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                st.session_state['process_handle'] = process
                status_placeholder.success("Process Started.")
            else:
                status_placeholder.info("Attached to running process.")

            # MONITORING LOOP
            # We cannot read process.stdout directly if we redirected to file
            # So we poll the file and live stats
            
            with open(log_file, "r") as f_read:
                pass

            while st.session_state['analyzing']:
                # Check health
                if process.poll() is not None:
                    st.session_state['analyzing'] = False
                    st.session_state['process_handle'] = None # Clear handle
                    
                    exit_code = process.returncode
                    
                    if exit_code == 0:
                        status_placeholder.success("Analysis Completed Successfully!")
                        st.balloons()
                    else:
                        status_placeholder.error(f"Process stopped unexpectedly with code {exit_code}")
                        
                        # Read Full Log for Debugging
                        error_log = "No log info."
                        if os.path.exists(log_file):
                            with open(log_file, "r") as f:
                                lines = f.readlines()
                                error_log = "".join(lines[-30:])
                        
                        st.error(f"### Crash Log (Code {exit_code})")
                        st.code(error_log)
                    
                    # Do not rerun automatically, let user digest error
                    break
                
                # 0. Live Video Preview (IPC)
                try:
                    if os.path.exists("data/live_frame.jpg"):
                        import cv2
                        img = cv2.imread("data/live_frame.jpg")
                        if img is not None:
                            # Convert BGR to RGB for Streamlit
                            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            video_placeholder.image(img_rgb, channels="RGB", use_column_width=True, caption="Live Analysis Feed")
                    else:
                        status_placeholder.info("Waiting for first frame...")
                except Exception as ex:
                    # status_placeholder.error(f"Frame Error: {ex}")
                    pass

                # 1. Update Logs
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        lines = f.readlines()
                        log_placeholder.code("".join(lines[-20:]))

                # 2. Update Live Dashboard
                try:
                    if os.path.exists("data/live_stats.json"):
                        with open("data/live_stats.json", "r") as f:
                            stats = json.load(f)
                        update_live_dashboard(dashboard_placeholders, stats)
                except:
                    pass
                
                # Sleep to prevent busy loop
                time.sleep(0.1) # Faster update for video smoothness

        except Exception as e:
            st.sidebar.error(f"Error: {e}")
            
        finally:
            # We don't rely on finally for stopping anymore, 
            # because st.rerun() might bypass it or we might toggle manually.
            # But if we exit the loop normally (unlikely unless error), we check.
            pass
