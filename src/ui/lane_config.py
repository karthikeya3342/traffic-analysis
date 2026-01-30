import streamlit as st
import cv2
import yaml
import numpy as np
import time
from PIL import Image

@st.cache_data
def get_first_frame(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    if ret:
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return None

def render_lane_config(config, selected_video):
    """
    Renders the lane configuration expander and canvas.
    Returns: None (Functions via callbacks/direct config modification)
    """
    if 'lane_canvas_key' not in st.session_state:
        st.session_state['lane_canvas_key'] = 0
    if 'last_lane_video' not in st.session_state:
        st.session_state['last_lane_video'] = None
    if 'force_lane_expand' not in st.session_state:
        st.session_state['force_lane_expand'] = False

    # Determine expander state: Auto-open if no lanes or if freshly refreshed
    has_lanes = len(config['analytics'].get('lanes', [])) > 0
    expanded_state = (not has_lanes) or st.session_state['force_lane_expand']

    with st.expander("Configure Lanes (Draw on Video)", expanded=expanded_state):
        # Reset force flag after using it
        if st.session_state['force_lane_expand']:
             st.session_state['force_lane_expand'] = False
             
        st.write("Draw rectangles on the video frame to define lanes.")
        
        # Check import
        try:
            from streamlit_drawable_canvas import st_canvas
        except ImportError:
            st.error("Please install the library: pip install streamlit-drawable-canvas")
            st.stop()

        if selected_video:
            # Auto-refresh on video change to fix initialization issues
            if st.session_state['last_lane_video'] != selected_video:
                st.session_state['last_lane_video'] = selected_video
                st.session_state['lane_canvas_key'] += 1
                st.session_state['force_lane_expand'] = True # Force open on refresh
                st.rerun()
            
            # Use cached frame getter
            frame_rgb = get_first_frame(selected_video)

            if frame_rgb is not None:
                # Resize logic (needs original dims from frame_rgb)
                h_orig, w_orig = frame_rgb.shape[:2]
                
                target_w = config['video'].get('resize_width', 1280)
                target_h = config['video'].get('resize_height', 720)
                
                # Resize using cv2 (need to convert back to BGR for resize? No, resize works on RGB)
                # But frame_rgb is numpy array.
                frame_resized_rgb = cv2.resize(frame_rgb, (target_w, target_h))

                # Resize for Canvas (Display only)
                canvas_width = 700
                h, w = frame_resized_rgb.shape[:2]
                scale_factor = canvas_width / w
                canvas_height = int(h * scale_factor)
                
                frame_pil = Image.fromarray(frame_resized_rgb)
                
                # Controls
                col_controls, col_canvas = st.columns([1, 3])
                
                with col_controls:
                    st.write("**Controls**")
                    mode = st.radio("Edit Mode", ["Lanes", "Stop Line"], horizontal=True)
                    
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button("Refresh", help="Refresh Image", use_container_width=True):
                            st.session_state['lane_canvas_key'] += 1
                            st.rerun()
                    with bc2:
                        if st.button("Clear", help="Clear Items", use_container_width=True):
                            if mode == "Lanes":
                                config['analytics']['lanes'] = []
                            else:
                                config['analytics']['stop_line_coords'] = []
                            
                            with open("config/config.yaml", "w") as f:
                                yaml.dump(config, f)
                            st.session_state['lane_canvas_key'] += 1 
                            st.rerun()
                    
                    st.caption("Delete points by selecting them and pressing Del.")

                # Prepare initial drawing
                initial_drawing = {"version": "4.4.0", "objects": []}
                
                if mode == "Lanes":
                    if 'lanes' in config['analytics']:
                        for lane in config['analytics']['lanes']:
                            coords = lane['coords']
                            points = []
                            if len(coords) == 4 and isinstance(coords[0], (int, float)):
                                x1, y1, x2, y2 = coords
                                points = [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]
                            else:
                                points = coords
                            
                            if points:
                                # Visual Path
                                scaled_path = []
                                start = points[0]
                                scaled_path.append(['M', start[0] * scale_factor, start[1] * scale_factor])
                                for p in points[1:]: 
                                    scaled_path.append(['L', p[0] * scale_factor, p[1] * scale_factor])
                                scaled_path.append(['Z'])
                                
                                initial_drawing['objects'].append({
                                    "type": "path",
                                    "path": scaled_path,
                                    "fill": "rgba(0, 255, 0, 0.2)",
                                    "stroke": "green",
                                    "strokeWidth": 1,
                                    "selectable": False,
                                    "evented": False
                                })
                                # Control Points
                                for p in points:
                                    initial_drawing['objects'].append({
                                        "type": "circle",
                                        "left": (p[0] * scale_factor) - 5,
                                        "top": (p[1] * scale_factor) - 5,
                                        "radius": 5, "fill": "red", "stroke": "white", "strokeWidth": 1
                                    })
                else: # Stop Line
                    stop_coords = config['analytics'].get('stop_line_coords')
                    points = []
                    if stop_coords and len(stop_coords) == 2:
                        points = stop_coords
                    else:
                        sy = config['analytics'].get('stop_line_y', 500)
                        points = [[100, sy], [w_orig-100, sy]]
                    
                    if points:
                        # Visual Line
                        p1, p2 = points[0], points[1]
                        initial_drawing['objects'].append({
                            "type": "line",
                            "x1": p1[0] * scale_factor,
                            "y1": p1[1] * scale_factor,
                            "x2": p2[0] * scale_factor,
                            "y2": p2[1] * scale_factor,
                            "stroke": "red",
                            "strokeWidth": 2,
                            "strokeDashArray": [5, 5],
                            "selectable": False, "evented": False
                        })
                        # Control Points
                        for p in points:
                            initial_drawing['objects'].append({
                                "type": "circle",
                                "left": (p[0] * scale_factor) - 5,
                                "top": (p[1] * scale_factor) - 5,
                                "radius": 5, "fill": "orange", "stroke": "white", "strokeWidth": 1
                            })

                # Create Canvas
                if mode == "Lanes":
                    st.write("👉 **Lanes**: Click 4 points to define a lane.")
                else:
                    st.write("👉 **Stop Line**: Click 2 points to define the line.")

                # Dynamic Key
                refresh_key = st.session_state['lane_canvas_key']
                unique_key = f"canvas_{selected_video}_{len(initial_drawing['objects'])}_{refresh_key}_{mode}"
                
                # DEBUG / GUARD: Ensure valid image for Cloud
                safe_bg = frame_pil
                # Ensure it is a PIL Image
                if not isinstance(safe_bg, Image.Image):
                    st.warning(f"Background image invalid type: {type(safe_bg)}. Using placeholder.")
                    safe_bg = Image.new("RGB", (canvas_width, canvas_height), (0, 0, 0))
                
                try:
                    canvas_result = st_canvas(
                        fill_color="rgba(0, 255, 0, 0.3)",
                        stroke_width=2,
                        stroke_color="green",
                        background_image=safe_bg,
                        update_streamlit=True,
                        height=canvas_height,
                        width=canvas_width,
                        drawing_mode="point",
                        point_display_radius=5,
                        initial_drawing=initial_drawing,
                        key=unique_key,
                    )
                except Exception as e:
                     st.error(f"Canvas Error: {e}")
                     return
                
                if canvas_result.json_data is not None:
                    objects = canvas_result.json_data["objects"]
                    
                    if st.button("💾 Save Configuration", use_container_width=True):
                        # Extract all circles (Points)
                        all_points = []
                        for obj in objects:
                            if obj["type"] == "circle":
                                r = obj.get("radius", 5)
                                x_center = obj["left"] + r
                                y_center = obj["top"] + r
                                x_orig = int(x_center / scale_factor)
                                y_orig = int(y_center / scale_factor)
                                all_points.append([x_orig, y_orig])
                        
                        if mode == "Lanes":
                            if len(all_points) % 4 != 0:
                                st.warning(f"⚠️ Lanes require exactly 4 points. Saving {len(all_points)//4} lanes.")

                            new_lane_config = []
                            num_lanes = len(all_points) // 4
                            for i in range(num_lanes):
                                lane_points = all_points[i*4 : (i+1)*4]
                                new_lane_config.append({
                                    "id": i+1,
                                    "name": f"Lane {i+1}",
                                    "coords": lane_points
                                })
                            config['analytics']['lanes'] = new_lane_config
                            st.success(f"✅ Saved {len(new_lane_config)} lanes!")
                            
                        else: # Stop Line
                            # Logic: If user added new points, they are at the end.
                            # If total points >= 2, default to the LAST 2 points.
                            if len(all_points) < 2:
                                st.error(f"⚠️ Stop Line requires at least 2 points. You have {len(all_points)}.")
                                return # Don't save
                            
                            if len(all_points) > 2:
                                st.warning(f"Found {len(all_points)} points. Using the last 2 points as the new Stop Line.")
                                all_points = all_points[-2:]
                            
                            config['analytics']['stop_line_coords'] = all_points
                            # Remove legacy Y to prefer coords
                            if 'stop_line_y' in config['analytics']:
                                del config['analytics']['stop_line_y']
                            st.success("✅ Stop Line Saved!")

                        # Write to file
                        with open("config/config.yaml", "w") as f:
                            yaml.dump(config, f)
                        
                        time.sleep(1) 
                        st.session_state['lane_canvas_key'] += 1
                        st.rerun()

            else:
                st.error("Could not read video frame.")
        else:
            st.info("Select a video to configure lanes.")
