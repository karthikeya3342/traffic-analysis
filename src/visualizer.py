import cv2
import numpy as np

class Visualizer:
    """
    Handles drawing annotations on video frames.
    """
    def __init__(self, config):
        self.config = config
        self.lanes = config['analytics'].get('lanes', [])
        self.stop_line_y = config['analytics'].get('stop_line_y', 500)
        self.stop_line_coords = config['analytics'].get('stop_line_coords', None)
        
        # Colors (BGR)
        self.colors = {
            'car': (0, 255, 0),
            'bus': (0, 255, 255),
            'truck': (255, 100, 0),
            'motorcycle': (255, 255, 0), # Cyan (Distinct from Rash/Magenta)
            'default': (200, 200, 200),
            'text': (255, 255, 255),
            'violation': (0, 0, 255),  # Red
            'rash': (255, 0, 255),       # Purple/Magenta
            'speeding': (0, 165, 255),   # Orange
            'roi': (255, 255, 0)
        }

    def draw_tracks(self, frame, tracks, bboxes, classes=None, violations=None):
        """
        Draw bounding boxes and IDs. Highlights violations.
        """
        # Create map for O(1) lookup
        violation_map = {}
        if violations:
            for v in violations:
                violation_map[v['id']] = v['reason']

        for obj_id, bbox in bboxes.items():
            try:
                x1, y1, x2, y2 = bbox
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Determine color based on class if available
                class_name = classes.get(obj_id, "Unknown") if classes else "Unknown"
                color = self.colors.get(class_name, self.colors['default'])
                
                # Check for Violations to override color
                extra_label = ""
                # Check for Violations to override color
                extra_label = ""
                
                # Robust Lookup (Handle int vs str mismatch)
                reason = violation_map.get(obj_id)
                if not reason:
                     reason = violation_map.get(str(obj_id))
                
                if reason:
                    if "Red Light" in reason:
                        color = self.colors['violation']
                        extra_label = " [RED LIGHT]"
                    elif "Speeding" in reason:
                        color = self.colors['speeding']
                        extra_label = " [SPEEDING]"
                    elif any(x in reason for x in ["Rash", "Acceleration", "Turning", "Aggression", "Lane Speed", "Brake"]):
                        color = self.colors['rash']
                        extra_label = " [RASH DRIVING]"
                
                label = f"ID: {obj_id} {class_name}{extra_label}"
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            except Exception as e:
                print(f"Error drawing track {obj_id}: {e}")
            
        return frame

    def draw_analytics(self, frame, queue_stats, violations, red_light_active=False, total_violations=None):
        """
        Draw analytics overlay: Queue counts, violations, and Traffic Signal.
        """
        overlay = frame.copy()
        
        # 1. Dashboard Background (Top Left for Stats)
        cv2.rectangle(overlay, (0, 0), (350, 160), (0, 0, 0), -1)
        
        # 2. Lane Queues
        y_offset = 30
        cv2.putText(overlay, "Queue Analytics:", (10, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_offset += 30
        
        for name, data in queue_stats.items():
            count = data['count']
            status = data['status']
            color = (0, 255, 0) if status == "Low" else (0, 255, 255) if status == "Medium" else (0, 0, 255)
            text = f"{name}: {count} ({status})"
            cv2.putText(overlay, text, (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
            y_offset += 25
            
            # Draw Lane Box on Overlay (Optional) or main frame
            # Let's simple draw the text here on dashboard. 
            # We will draw the actual ROIs later on the main frame.
            
        # 3. Violation Summary
        if total_violations is None:
            total_violations = len(set(v['id'] for v in violations))
            
        cv2.putText(overlay, f"Violations: {total_violations}", (10, y_offset + 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # 4. Traffic Signal Visual (Top Center)
        # Housing
        signal_x, signal_y = 640, 10
        cv2.rectangle(overlay, (signal_x, signal_y), (signal_x + 60, signal_y + 110), (20, 20, 20), -1)
        cv2.rectangle(overlay, (signal_x, signal_y), (signal_x + 60, signal_y + 110), (100, 100, 100), 2)
        
        # Light Colors
        red_color = (0, 0, 255) if red_light_active else (0, 0, 50)
        green_color = (0, 255, 0) if not red_light_active else (0, 50, 0)
        
        # Red Light (Top)
        cv2.circle(overlay, (signal_x + 30, signal_y + 30), 20, red_color, -1)
        
        # Green Light (Bottom)
        cv2.circle(overlay, (signal_x + 30, signal_y + 80), 20, green_color, -1)
        
        # Status Text
        state_text = "STOP" if red_light_active else "GO"
        text_color = (0, 0, 255) if red_light_active else (0, 255, 0)
        cv2.putText(overlay, state_text, (signal_x, signal_y + 135), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2)
        
        # Blend
        alpha = 0.6
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        
        # Draw Stop Line directly on frame (no transparency) if Red Light is Active
        # to emphasize the rule
        
        # Determine Stop Line Points
        stop_line_p1, stop_line_p2 = None, None
        if self.stop_line_coords and len(self.stop_line_coords) == 2:
            stop_line_p1 = tuple(self.stop_line_coords[0])
            stop_line_p2 = tuple(self.stop_line_coords[1])
        elif self.stop_line_y:
            h, w = frame.shape[:2]
            stop_line_p1 = (0, self.stop_line_y)
            stop_line_p2 = (w, self.stop_line_y)
            
        if stop_line_p1 and stop_line_p2:
            if red_light_active:
                 cv2.line(frame, stop_line_p1, stop_line_p2, (0, 0, 255), 3)
                 label_pos = (max(0, stop_line_p1[0] + 10), max(20, stop_line_p1[1] - 10))
                 cv2.putText(frame, "STOP LINE ACTIVE", label_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            else:
                 cv2.line(frame, stop_line_p1, stop_line_p2, (0, 255, 0), 2)
                 label_pos = (max(0, stop_line_p1[0] + 10), max(20, stop_line_p1[1] - 10))
                 cv2.putText(frame, "STOP LINE", label_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

        # Draw Lanes (ROIs)
        for name, data in queue_stats.items():
            if 'coords' in data:
                coords = data['coords']
                # Determine color based on density (Low=Green, Med=Yellow, High=Red)
                status = data.get('status', 'Low')
                color = (0, 255, 0) # Green
                if status == 'Medium': color = (0, 255, 255)
                if status == 'High': color = (0, 0, 255)
                
                # Draw ROI Polygon
                pts = np.array(coords, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, color, 2)
                
                # Draw Label on Frame (at first point)
                label_pos = (coords[0][0], coords[0][1] - 5)
                cv2.putText(frame, name, label_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Draw Violations (Right Side)
        h, w = frame.shape[:2]
        x_start = w - 450
        y_off = 50
        
        if violations:
             # Limit to 5 annotations to prevent flooding
             violations_to_show = violations[:5]
             
             # Draw Background for readability
             count = len(violations_to_show)
             box_h = count * 35 + 20
             overlay_v = frame.copy()
             cv2.rectangle(overlay_v, (x_start - 10, y_off - 30), (w - 10, y_off + box_h), (0, 0, 0), -1)
             cv2.addWeighted(overlay_v, 0.6, frame, 0.4, 0, frame)

             cv2.putText(frame, "VIOLATION ALERT", (x_start, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
             y_off += 35
             
             for v in violations_to_show:
                 text = f"ID {v['id']}: {v['reason']}"
                 cv2.putText(frame, text, (x_start, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                 y_off += 30
            
        return frame
