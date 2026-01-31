import numpy as np
from .utils import point_in_polygon, calculate_iou, segments_intersect

class TrafficAnalytics:
    """
    Handles queue estimation and violation detection.
    """
    def __init__(self, config):
        self.config = config
        self.lanes = config['analytics'].get('lanes', [])
        # Legacy support
        self.stop_line_y = config['analytics'].get('stop_line_y', 500)
        # New Segment support
        self.stop_line_coords = config['analytics'].get('stop_line_coords', None)
        
        self.violation_thresholds = config['analytics'].get('violation_thresholds', {})
        
        # State for violations
        self.red_light_violations = set() # Set of object IDs
        self.rash_driving_violations = set() # Set of object IDs
        self.rash_counters = {} # {obj_id: consecutive_frames}
        
        # Metadata storage for persistent violations
        self.rash_details = {} # {obj_id: {'reason': ..., 'confidence': ...}}
        
        # NEW STATE for Heuristics
        self.speed_history = {} # {id: [s1, s2, s3, s4, s5]}

    def update_queues(self, tracks, bboxes):
        """
        Estimate queue density using Area-Based Occupancy:
        Density = Sum(Vehicle BBox Intersection with Lane) / Total Lane Area
        """
        import cv2
        
        # Lazy Init of Lane Masks
        if not hasattr(self, 'lane_masks'):
            self.lane_masks = {}
            h = self.config['video'].get('resize_height', 720)
            w = self.config['video'].get('resize_width', 1280)
            
            for lane in self.lanes:
                mask = np.zeros((h, w), dtype=np.uint8)
                pts = np.array(lane['coords'], dtype=np.int32)
                cv2.fillPoly(mask, [pts], 255)
                # Calculate total lane area
                area = np.count_nonzero(mask)
                self.lane_masks[lane['name']] = {'mask': mask, 'area': area}

        queue_stats = {}
        
        # Initialize Stats
        for lane in self.lanes:
            queue_stats[lane['name']] = {
                "count": 0, 
                "occupancy_pixels": 0,
                "density_ratio": 0.0,
                "status": "Free Flow",
                "coords": lane['coords']
            }
            
        # Calculate Intersections
        # Optimization: Only iterate lanes that exist
        if not self.lane_masks: return queue_stats

        for obj_id, bbox in bboxes.items():
            x1, y1, x2, y2 = map(int, bbox)
            
            # Clip to frame dimensions
            h_frame, w_frame = self.lane_masks[self.lanes[0]['name']]['mask'].shape
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_frame, x2), min(h_frame, y2)
            
            if x2 <= x1 or y2 <= y1: continue
            
            # Check intersection with each lane
            for lane_name, lane_data in self.lane_masks.items():
                mask = lane_data['mask']
                
                # Extract ROI from mask corresponding to vehicle bbox
                # This ROI contains 255 where Lane exists, 0 otherwise.
                # All pixels in this ROI are "Inside the Vehicle BBox" by definition.
                # So counting non-zero in this ROI = Area(Lane Intersect Vehicle)
                roi = mask[y1:y2, x1:x2]
                intersection_area = np.count_nonzero(roi)
                
                if intersection_area > 0:
                     queue_stats[lane_name]['occupancy_pixels'] += intersection_area
                     
                     # Count vehicle if it overlaps significantly (>5% of its own area or >100 pixels)
                     # or just >0 for raw sensitivity. Let's use >0.
                     queue_stats[lane_name]['count'] += 1

        # Calculate Final Density
        for name, stats in queue_stats.items():
            total_lane_area = self.lane_masks[name]['area']
            if total_lane_area > 0:
                stats['density_ratio'] = stats['occupancy_pixels'] / total_lane_area
            else:
                stats['density_ratio'] = 0
            
            # Thresholds
            dr = stats['density_ratio']
            if dr > 0.40: stats['status'] = "Congested"
            elif dr > 0.15: stats['status'] = "Moderate"
            else: stats['status'] = "Free Flow"
            
        return queue_stats

    def check_red_light_violations(self, tracks, history, red_light_active=True):
        """
        Check if vehicles cross the stop line segments when red light is active.
        """
        if not red_light_active:
            return []

        new_violations = []
        
        # Determine Stop Line Segment (p1, p2)
        start_pt, end_pt = None, None
        if self.stop_line_coords and len(self.stop_line_coords) == 2:
            start_pt, end_pt = self.stop_line_coords
        else:
            # Fallback to horizontal line at stop_line_y
            stop_y = self.stop_line_y
            start_pt = (0, stop_y)
            end_pt = (3000, stop_y) # Arbitrary large width coverage in X

        for obj_id, centroid in tracks.items():
            if obj_id in self.red_light_violations:
                continue
                
            if len(history[obj_id]) < 3:
                continue
            
            prev_centroid = history[obj_id][-2]
            curr_centroid = centroid
            
            # Intersection Check: Vehicle Path vs Stop Line
            # Vehicle Path Segment: prev -> curr
            # Stop Line Segment: start_pt -> end_pt
            if segments_intersect(prev_centroid, curr_centroid, start_pt, end_pt):
                 self.red_light_violations.add(obj_id)
                 new_violations.append(obj_id)
                    
        return new_violations

    def check_speeding(self, tracks, history):
        """
        Detect vehicles moving faster than the pixel threshold per frame.
        """
        speeding_violations = []
        limit = self.config['analytics'].get('speed_limit_pixels', 25)
        
        for obj_id, path in history.items():
            if len(path) < 2:
                continue
                
            p_curr = np.array(path[-1])
            p_prev = np.array(path[-2])
            
            speed = np.linalg.norm(p_curr - p_prev)
            
            if speed > limit:
                speeding_violations.append({
                    "id": obj_id,
                    "reason": "Speeding",
                    "confidence": "Medium"
                })
                
        return speeding_violations

    def detect_rash_driving(self, tracks, history, red_light_active=False):
        """
        Detect rash driving using heuristic scoring:
        - Speed Spike (vs self history) (+1)
        - Lane Speed Deviation (vs lane average) (+1)
        - Abrupt Turning (Zig-Zag) (+1)
        - Stop Line Aggression (Red Light crossing) (+2)
        
        Score >= 4: HIGH
        Score >= 2: MEDIUM
        """
        import logging
        
        # Ensure metadata storage exists
        if not hasattr(self, 'rash_details'): self.rash_details = {}
        if not hasattr(self, 'speed_history'): self.speed_history = {}

        # 1. Calculate Speeds & Assign Lanes
        current_speeds = {} # {id: pixels_per_frame}
        vehicle_lanes = {}  # {id: lane_name}
        lane_speeds = {lane['name']: [] for lane in self.lanes}
        
        for obj_id, path in history.items():
            if len(path) < 2: continue
            
            p_curr = np.array(path[-1])
            p_prev = np.array(path[-2])
            speed = np.linalg.norm(p_curr - p_prev)
            current_speeds[obj_id] = speed
            
            # Update History
            if obj_id not in self.speed_history: self.speed_history[obj_id] = []
            self.speed_history[obj_id].append(speed)
            if len(self.speed_history[obj_id]) > 5: self.speed_history[obj_id].pop(0)

            # Assign Lane (for dynamic context)
            if obj_id in tracks:
                centroid = tracks[obj_id]
                for lane in self.lanes:
                    if point_in_polygon(centroid, lane['coords']):
                        vehicle_lanes[obj_id] = lane['name']
                        lane_speeds[lane['name']].append(speed)
                        break
        
        # Calculate Lane Averages
        lane_avg_speeds = {}
        for name, speeds in lane_speeds.items():
            lane_avg_speeds[name] = sum(speeds) / len(speeds) if speeds else 0

        # PARAMETERS
        MIN_SPEED = 8.0         # Reduced from 15 to catch city speeds
        ACCEL_THRESH = 1.6      # Reduced from 2.0 (60% increase)
        BRAKE_THRESH = 0.7      # Increased from 0.5 (30% drop is enough)
        LANE_SPEED_THRESH = 1.6 # Reduced from 1.8

        # 2. Evaluate Heuristics
        for obj_id, path in history.items():
            if len(path) < 5: continue # Minimum context required
            if obj_id not in current_speeds: continue
            
            speed = current_speeds[obj_id]
            hist = self.speed_history.get(obj_id, [])
            avg_hist = sum(hist) / len(hist) if hist else speed
            
            # Debug Log for tuning (visible in console)
            # if speed > 5 or avg_hist > 5:
            #    logging.info(f"ID {obj_id} | Spd: {speed:.1f} | Avg: {avg_hist:.1f} | LaneAvg: {lane_avg_speeds.get(vehicle_lanes.get(obj_id), 0):.1f}")

            score = 0
            reasons = []
            
            # A. Speed Spike (vs Self)
            # Acceleration: Current > 1.6x Avg
            if avg_hist > 2 and speed > MIN_SPEED and speed > (avg_hist * ACCEL_THRESH):
                score += 1
                reasons.append("Sudden Accel")
            
            # Deceleration: Current < 0.7x Avg (Sudden Stop/Brake)
            if avg_hist > MIN_SPEED and speed < (avg_hist * BRAKE_THRESH):
                score += 1
                reasons.append("Sudden Brake")

            # B. Lane Deviation (vs Lane)
            lane_name = vehicle_lanes.get(obj_id)
            if lane_name:
                l_avg = lane_avg_speeds.get(lane_name, 0)
                if l_avg > 2 and speed > MIN_SPEED and speed > (l_avg * LANE_SPEED_THRESH):
                    score += 1
                    reasons.append("High Lane Speed")
            
            # C. Aggressive Turning (Zig-Zag)
            p3 = np.array(path[-1])
            p2 = np.array(path[-2])
            p1 = np.array(path[-3])
            v1 = p2 - p1
            v2 = p3 - p2
            if np.linalg.norm(v1) > 5 and np.linalg.norm(v2) > 5:
                # Dot product
                cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                angle = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))
                if angle > 30: # 30 degrees
                    score += 1
                    reasons.append("Aggressive Turn")
            
            # D. Stop Line Aggression
            # Logic: If Red Light Active AND Crossed Line in this frame step
            if red_light_active:
                # Determine stop line logic again (stateful access)
                start_pt, end_pt = None, None
                if self.stop_line_coords and len(self.stop_line_coords) == 2:
                    start_pt, end_pt = self.stop_line_coords
                elif self.stop_line_y:
                    start_pt, end_pt = (0, self.stop_line_y), (3000, self.stop_line_y)
                
                # Check intersection of LAST step (prev -> curr)
                if start_pt and segments_intersect(path[-2], path[-1], start_pt, end_pt):
                     score += 2
                     reasons.append("Stop Aggression")

            # 3. Decision & Persistence
            if obj_id not in self.rash_counters: self.rash_counters[obj_id] = 0
            
            current_confidence = "Low"
            is_rash = False
            
            if score >= 4:
                current_confidence = "High"
                is_rash = True
                # Boost counter for immediate trigger (High confidence needs no persistence)
                self.rash_counters[obj_id] = max(self.rash_counters[obj_id], 1) 
            elif score >= 2:
                current_confidence = "Medium"
                is_rash = True
            
            if is_rash:
                self.rash_counters[obj_id] += 1
                logging.info(f"RASH CANDIDATE ID {obj_id}: Score={score} Reasons={reasons} Count={self.rash_counters[obj_id]}")
                
                # Threshold check (Immediate for High, 2 for Medium)
                threshold = 2
                if current_confidence == "High": threshold = 2 # Actually, logic above +1 makes it 2 if started at 1. 
                # Let's simplify: High confidence triggers immediately.
                if current_confidence == "High": threshold = 1
                
                if self.rash_counters[obj_id] >= threshold: 
                    if obj_id not in self.rash_driving_violations:
                        logging.info(f"CONFIRMED RASH VIOLATION ID {obj_id} - {reasons}")
                    self.rash_driving_violations.add(obj_id)
                    
                    # Determine primary reason for display
                    primary_reason = reasons[0] if reasons else "Rash Driving"
                    if "Stop Aggression" in reasons: primary_reason = "Signal Aggression"
                    elif len(reasons) > 1: primary_reason = "Rash Driving"
                    
                    self.rash_details[obj_id] = {
                        "reason": primary_reason,
                        "confidence": current_confidence,
                        "score": score
                    }
            else:
                if self.rash_counters[obj_id] > 0:
                    self.rash_counters[obj_id] -= 1
        
        # Return ALL currently active violations with specific reasons
        active_rash_drivers = []
        for obj_id in self.rash_driving_violations:
            details = self.rash_details.get(obj_id, {"reason": "Rash Driving", "confidence": "Medium"})
            active_rash_drivers.append({
                "id": obj_id,
                "reason": details["reason"],
                "confidence": details["confidence"]
            })
            
        return active_rash_drivers
