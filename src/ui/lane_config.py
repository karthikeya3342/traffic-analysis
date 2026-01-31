import streamlit as st
import cv2
import yaml
import numpy as np
import time
from PIL import Image
import os

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

    if 'lane_canvas_key' not in st.session_state:
        st.session_state['lane_canvas_key'] = 0
    if 'last_lane_video' not in st.session_state:
        st.session_state['last_lane_video'] = None
    if 'force_lane_expand' not in st.session_state:
        st.session_state['force_lane_expand'] = False

    has_lanes = len(config['analytics'].get('lanes', [])) > 0
    expanded_state = (not has_lanes) or st.session_state['force_lane_expand']

    with st.expander("Configure Lanes (Draw on Video)", expanded=expanded_state):

        if st.session_state['force_lane_expand']:
            st.session_state['force_lane_expand'] = False

        st.write("Draw rectangles on the video frame to define lanes.")

        try:
            from streamlit_drawable_canvas import st_canvas
        except ImportError:
            st.error("Install: pip install streamlit-drawable-canvas")
            st.stop()

        if selected_video:

            if st.session_state['last_lane_video'] != selected_video:
                st.session_state['last_lane_video'] = selected_video
                st.session_state['lane_canvas_key'] += 1
                st.session_state['force_lane_expand'] = True
                st.rerun()

            st.write(
                f"DEBUG: Video Path: {selected_video} | Exists: {os.path.exists(selected_video)}"
            )

            frame_rgb = get_first_frame(selected_video)

            if frame_rgb is None:
                st.error("Could not read video frame.")
                return

            h_orig, w_orig = frame_rgb.shape[:2]

            canvas_width = 700
            scale_factor = canvas_width / w_orig
            canvas_height = int(h_orig * scale_factor)

            # ✅ FIXED: FORCE RGB (NO RGBA)
            bg_image = Image.fromarray(frame_rgb).convert("RGB")
            bg_image = bg_image.resize(
                (canvas_width, canvas_height), Image.Resampling.LANCZOS
            )

            # 🔒 Safety guard
            if bg_image.mode != "RGB":
                bg_image = bg_image.convert("RGB")

            col_controls, col_canvas = st.columns([1, 3])

            with col_controls:
                st.write("**Controls**")
                mode = st.radio("Edit Mode", ["Lanes", "Stop Line"], horizontal=True)

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Refresh", use_container_width=True):
                        st.session_state['lane_canvas_key'] += 1
                        st.rerun()
                with c2:
                    if st.button("Clear", use_container_width=True):
                        if mode == "Lanes":
                            config['analytics']['lanes'] = []
                        else:
                            config['analytics']['stop_line_coords'] = []

                        with open("config/config.yaml", "w") as f:
                            yaml.dump(config, f)

                        st.session_state['lane_canvas_key'] += 1
                        st.rerun()

                st.write("---")
                st.caption("Reference image (should NEVER be black)")
                st.image(bg_image, use_column_width=True)

            # ---------------- INITIAL DRAWING ----------------
            initial_drawing = {"version": "4.4.0", "objects": []}

            if mode == "Lanes":
                for lane in config['analytics'].get('lanes', []):
                    points = lane["coords"]
                    scaled = []

                    start = points[0]
                    scaled.append(['M', start[0]*scale_factor, start[1]*scale_factor])
                    for p in points[1:]:
                        scaled.append(['L', p[0]*scale_factor, p[1]*scale_factor])
                    scaled.append(['Z'])

                    initial_drawing["objects"].append({
                        "type": "path",
                        "path": scaled,
                        "fill": "rgba(0,255,0,0.2)",
                        "stroke": "green",
                        "strokeWidth": 1,
                        "selectable": False,
                        "evented": False
                    })

            st.write(
                "👉 **Lanes**: Click 4 points" if mode == "Lanes"
                else "👉 **Stop Line**: Click 2 points"
            )

            refresh_key = st.session_state['lane_canvas_key']
            unique_key = f"canvas_{selected_video}_{refresh_key}_{mode}"

            canvas_result = st_canvas(
                fill_color="rgba(0,255,0,0.3)",
                stroke_width=2,
                stroke_color="green",
                background_image=bg_image,
                update_streamlit=True,
                height=canvas_height,
                width=canvas_width,
                drawing_mode="point",
                point_display_radius=5,
                initial_drawing=initial_drawing,
                key=unique_key,
            )

            if canvas_result.json_data and st.button("💾 Save Configuration"):
                objects = canvas_result.json_data["objects"]
                points = []

                for obj in objects:
                    if obj["type"] == "circle":
                        r = obj.get("radius", 5)
                        x = int((obj["left"] + r) / scale_factor)
                        y = int((obj["top"] + r) / scale_factor)
                        points.append([x, y])

                if mode == "Lanes":
                    config['analytics']['lanes'] = [
                        {"id": i+1, "name": f"Lane {i+1}", "coords": points[i*4:(i+1)*4]}
                        for i in range(len(points)//4)
                    ]
                else:
                    config['analytics']['stop_line_coords'] = points[-2:]

                with open("config/config.yaml", "w") as f:
                    yaml.dump(config, f)

                st.success("✅ Configuration saved!")
                time.sleep(1)
                st.session_state['lane_canvas_key'] += 1
                st.rerun()

        else:
            st.info("Select a video to configure lanes.")
