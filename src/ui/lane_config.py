import streamlit as st
import cv2
import yaml
import numpy as np
import time
from PIL import Image

# ... (get_first_frame remains same) ...

# @st.cache_data removed for debugging
def get_first_frame(video_path):
    cap = cv2.VideoCapture(video_path)
    for _ in range(30):
        ret, frame = cap.read()
        if ret and frame is not None and np.sum(frame) > 0:
            cap.release()
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    cap.release()
    return None

def render_lane_config(config, selected_video):
    # Initialize Session State
    if 'lane_temp_points' not in st.session_state:
        st.session_state['lane_temp_points'] = []
    if 'stop_temp_points' not in st.session_state:
        st.session_state['stop_temp_points'] = []
    if 'last_click' not in st.session_state:
        st.session_state['last_click'] = None

    with st.expander("Configure Lanes (Click to Draw)", expanded=True):
        try:
            from streamlit_image_coordinates import streamlit_image_coordinates
        except ImportError:
            st.error("Please install: pip install streamlit-image-coordinates")
            return

        if not selected_video:
            st.info("Select a video first.")
            return

        frame_rgb = get_first_frame(selected_video)
        if frame_rgb is None:
            st.error("Could not load video.")
            return

        # Resize for display
        target_w = 700
        h, w = frame_rgb.shape[:2]
        ratio = target_w / w
        target_h = int(h * ratio)
        
        # Working Copy for Visualization
        display_frame = cv2.resize(frame_rgb, (target_w, target_h))
        
        # --- DRAWING LOGIC (Server-Side) ---
        mode = st.radio("Mode", ["Lanes", "Stop Line", "Preview Config"], horizontal=True)
        
        # Draw Existing Config
        if mode == "Preview Config":
             # Draw Lanes from Config
             for lane in config['analytics'].get('lanes', []):
                 pts = np.array(lane['coords'], dtype=np.int32)
                 # Scale to display
                 pts = (pts * ratio).astype(np.int32)
                 cv2.polylines(display_frame, [pts], True, (0, 255, 0), 2)
                 centroid = np.mean(pts, axis=0).astype(int)
                 cv2.putText(display_frame, str(lane.get('id', '?')), tuple(centroid), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
             # Draw Stop Line
             stop_pts = config['analytics'].get('stop_line_coords', [])
             if len(stop_pts) == 2:
                 p1 = (int(stop_pts[0][0] * ratio), int(stop_pts[0][1] * ratio))
                 p2 = (int(stop_pts[1][0] * ratio), int(stop_pts[1][1] * ratio))
                 cv2.line(display_frame, p1, p2, (255, 0, 0), 3)

        # Draw Temp Points (Interactive)
        current_points = st.session_state['lane_temp_points'] if mode == "Lanes" else st.session_state['stop_temp_points']
        
        # Draw completed polygons/lines currently in buffer
        if mode == "Lanes":
            # Draw completed quads
            for i in range(0, len(current_points), 4):
                chunk = current_points[i:i+4]
                if len(chunk) == 4:
                     pts = np.array(chunk, dtype=np.int32)
                     cv2.polylines(display_frame, [pts], True, (0, 255, 0), 2)
            # Draw active uncompleted points
            remainder = len(current_points) % 4
            if remainder > 0:
                 active = current_points[-remainder:]
                 for pt in active:
                     cv2.circle(display_frame, tuple(pt), 4, (255, 165, 0), -1)

        elif mode == "Stop Line":
            if (len(current_points) == 2):
                 cv2.line(display_frame, tuple(current_points[0]), tuple(current_points[1]), (255, 0, 0), 2)
            for pt in current_points:
                cv2.circle(display_frame, tuple(pt), 4, (255, 165, 0), -1)

        # --- INTERACTION ---
        st.write(f"**Instructions**: Click on the image to add points. Mode: {mode}")
        if mode == "Lanes":
            st.caption(f"Points: {len(current_points)} (Needs multiple of 4)")
        elif mode == "Stop Line":
            st.caption(f"Points: {len(current_points)}/2")

        # Render Interface
        value = streamlit_image_coordinates(
            Image.fromarray(display_frame),
            key="click_interaction",
            width=target_w,
        )

        # Handle Click
        if value is not None and value != st.session_state['last_click']:
            st.session_state['last_click'] = value
            x = value['x']
            y = value['y']
            
            if mode != "Preview Config":
                # Add point (server-side list)
                if mode == "Lanes":
                    st.session_state['lane_temp_points'].append([x, y])
                else:
                    if len(st.session_state['stop_temp_points']) < 2:
                         st.session_state['stop_temp_points'].append([x, y])
                    else:
                         # Reset if full
                         st.session_state['stop_temp_points'] = [[x, y]]
                st.rerun()

        # Save/Clear Controls
        c1, c2 = st.columns(2)
        if c1.button("Clear Current Points"):
            if mode == "Lanes":
                st.session_state['lane_temp_points'] = []
            elif mode == "Stop Line":
                st.session_state['stop_temp_points'] = []
            st.rerun()
            
        if c2.button("💾 Save to Config"):
            # Scaling: Map from Display (700px) -> Processing Resolution (e.g. 1280px)
            # NOT Original Resolution, because main.py resizes the frame.
            process_w = config['video'].get('resize_width', 1280)
            process_h = config['video'].get('resize_height', 720)
            
            scale_x = process_w / target_w
            scale_y = process_h / target_h
            
            if mode == "Lanes":
                lanes_data = []
                pts = st.session_state['lane_temp_points']
                if len(pts) > 0 and len(pts) % 4 == 0:
                    for i in range(len(pts) // 4):
                        # Get 4 points, scale them
                        poly = []
                        for p in pts[i*4 : (i+1)*4]:
                            # Scale x by scale_x, y by scale_y
                            px = int(p[0] * scale_x)
                            py = int(p[1] * scale_y)
                            poly.append([px, py])
                        
                        lanes_data.append({
                            "id": i+1,
                            "name": f"Lane {i+1}",
                            "coords": poly
                        })
                    config['analytics']['lanes'] = lanes_data
                    st.success(f"Saved {len(lanes_data)} lanes!")
                else:
                    st.error("Need exactly 4 points per lane.")
                    
            elif mode == "Stop Line":
                pts = st.session_state['stop_temp_points']
                if len(pts) == 2:
                    p1 = [int(pts[0][0] * scale_x), int(pts[0][1] * scale_y)]
                    p2 = [int(pts[1][0] * scale_x), int(pts[1][1] * scale_y)]
                    config['analytics']['stop_line_coords'] = [p1, p2]
                    # Clean legacy
                    if 'stop_line_y' in config['analytics']:
                        del config['analytics']['stop_line_y']
                    st.success("Stop line saved!")
                else:
                    st.error("Need exactly 2 points.")

            with open("config/config.yaml", "w") as f:
                yaml.dump(config, f)
            
            st.warning("⚠️ NOTE: You must RESTART the analysis (Click Stop -> Start) to apply these changes!")
            time.sleep(2)
            st.rerun()
