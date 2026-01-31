import yaml
import cv2
import time
import logging
import os
import json
from src.loader import VideoLoader
from src.detector import MockDetector, YoloDetector
from src.tracker import SimpleTracker
from src.analytics import TrafficAnalytics
from src.visualizer import Visualizer
from src.utils import get_centroid

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(path="config/config.yaml"):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, help="Path to input video file", default=None)
    args = parser.parse_args()

    try:
        config = load_config()
    
        # Override config if CLI arg provided
        if args.source:
            config['video']['source'] = args.source
            logging.info(f"Overriding video source: {args.source}")
        
        # Initialize modules
        loader = VideoLoader(config['video']['source'], 
                             resize_dim=(config['video']['resize_width'], config['video']['resize_height']))
        
        # Use MockDetector if YOLO is not available or for testing
        # detector = MockDetector(width=config['video']['resize_width'], height=config['video']['resize_height'])
        try:
            detector = YoloDetector(model_path=config['detection']['model'], 
                                    conf_thres=config['detection']['confidence_threshold'],
                                    classes=config['detection']['classes'])
        except Exception as e:
            logging.warning(f"Failed to load YOLO: {e}. Using MockDetector.")
            detector = MockDetector(width=config['video']['resize_width'], height=config['video']['resize_height'])
        tracker = SimpleTracker(max_disappeared=config['tracking']['max_disappeared'],
                                max_distance=config['tracking']['max_distance'])
        
        analytics = TrafficAnalytics(config)
        visualizer = Visualizer(config)
        
        # Video Writer
        # Use 'avc1' (H.264) for better browser compatibility in Streamlit
        try:
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
        except:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Fallback
            
        out = cv2.VideoWriter(config['video']['output'], fourcc, config['video']['fps'], 
                              (config['video']['resize_width'], config['video']['resize_height']))
        
        logging.info("Starting processing...")
        
        # Stats for dashboard (could be written to a file/db)
        all_stats = []
        total_unique_violations = set()
        
        from collections import deque
        recent_violations_deque = deque(maxlen=10)
    
                # State for analytics
        total_unique_violations = set()
        total_unique_ids = set() # Track all unique vehicles for classification
        class_counts = {} # { 'car': 0, 'bus': 0 ... }
        display_violations = {} # {id: {'data': v, 'expiry': timestamp}}
        
        from collections import deque, Counter
        # Queue for on-screen annotations (Latest 5, persistent until replaced)
        annotation_queue = deque(maxlen=5) 
        # Full log for dashboard
        session_violations = [] # List of dicts
        
        # Class Stability Tracking
        class_history = {} # {id: Counter()}
    
        # INNER TRY (Loop)
        try:
            for frame_id, frame in loader:
                # ... (Stop signal check omitted for brevity, logic remains) ...
                if os.path.exists("data/.stop_signal"):
                     # ... existing code ...
                     logging.info("Stop signal received. Finishing processing...")
                     try: os.remove("data/.stop_signal")
                     except: pass
                     break
    
                start_time = time.time()
                
                # ... (Detection logic remains) ...
                detections = detector.detect(frame)
                
                # ... (Object parsing remains) ...
                objects = {}
                bboxes = {}
                classes = {}
                current_ids = set()
                
                for d in detections:
                     # ... (Unchanged) ...
                     obj_id = d['track_id']
                     centroid = get_centroid(d['bbox'])
                     
                     # --- Class Stability/Voting ---
                     if obj_id not in class_history:
                         class_history[obj_id] = Counter()
                     class_history[obj_id][d['class_name']] += 1
                     
                     # Get the most frequent class for this ID
                     dominant_class = class_history[obj_id].most_common(1)[0][0]
                     
                     objects[obj_id] = centroid
                     bboxes[obj_id] = d['bbox']
                     classes[obj_id] = dominant_class # STABLE CLASS
                     current_ids.add(obj_id)
                     if obj_id not in tracker.history: tracker.history[obj_id] = []
                     tracker.history[obj_id].append(centroid)
                     if len(tracker.history[obj_id]) > 20: tracker.history[obj_id].pop(0)
    
                # ... (Signal State check unchanged) ...
                red_light_active = False
                try:
                    if os.path.exists("data/signal_state.txt"):
                        with open("data/signal_state.txt", "r") as f:
                            if f.read().strip() == "RED": red_light_active = True
                except: pass
    
                # 3. Analytics
                queue_stats = analytics.update_queues(objects, bboxes)
                
                # Check violations
                red_light_violations = analytics.check_red_light_violations(objects, tracker.history, red_light_active=red_light_active)
                rash_drivers = analytics.detect_rash_driving(objects, tracker.history, red_light_active=red_light_active)
                # speeders = analytics.check_speeding(objects, tracker.history) # Disabled per user request
                
                # Aggregate violations for display
                current_violations = []
                for vid in red_light_violations:
                    current_violations.append({"id": vid, "reason": "Red Light", "confidence": "High"})
                current_violations.extend(rash_drivers)
                # current_violations.extend(speeders)
                
                # Update Unique Violations Count
                for v in current_violations:
                    if v['id'] not in total_unique_violations:
                        logging.info(f"New Violation Detected: ID {v['id']} ({v['reason']})")
                        total_unique_violations.add(v['id'])
                        
                        # Add to full session log
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                        violation_record = {
                            "time": timestamp,
                            "vehicle_id": v['id'],
                            "type": v['reason']
                        }
                        session_violations.append(violation_record)
                        
                        # Add to on-screen annotation queue (Latest 5)
                        annotation_queue.appendleft(v)
    
                # Update Vehicle Classification Counts
                for obj_id in current_ids:
                    if obj_id not in total_unique_ids:
                        total_unique_ids.add(obj_id)
                        cls_name = classes.get(obj_id, "Unknown")
                        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
    
                # --- PERSISTENCE LOGIC START ---
                now = time.time()
                # 1. Update/Refresh timestamps for currently detected violations (Red Boxes)
                for v in current_violations:
                    display_violations[v['id']] = {
                        'data': v,
                        'expiry': now + 2.0 # Keep red box visible for 2 seconds
                    }
                
                visible_violations = []
                keys_to_remove = []
                for vid, item in display_violations.items():
                    if now < item['expiry']:
                        visible_violations.append(item['data'])
                    else:
                        keys_to_remove.append(vid)
                for k in keys_to_remove: del display_violations[k]
                # --- PERSISTENCE LOGIC END ---
    
                # 4. Visualization
                # Use visible_violations for drawing boxes (Transient red boxes)
                frame = visualizer.draw_tracks(frame, objects, bboxes, classes=classes, violations=visible_violations)
                
                # Use annotation_queue for overlay text (Persistent latest 5 list)
                frame = visualizer.draw_analytics(frame, queue_stats, list(annotation_queue), 
                                                  red_light_active=red_light_active,
                                                  total_violations=len(total_unique_violations))
                
                # Save/Show
                out.write(frame)
                
                # Save Live Frame for Streamlit Preview (IPC)
                if frame_id % 3 == 0:
                    try:
                        cv2.imwrite("data/live_frame.tmp.jpg", frame)
                        os.replace("data/live_frame.tmp.jpg", "data/live_frame.jpg")
                    except:
                        pass
                # cv2.imshow("Traffic Analysis", frame) # Disabled for headless/agent env
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break
                
                # Log stats
                frame_stats = {
                    "frame": frame_id,
                    "vehicle_count": len(objects),
                    "queue_stats": queue_stats,
                    "violations": len(current_violations)
                }
                all_stats.append(frame_stats)
    
                # --- SAVE LIVE STATS (Near-Real-Time) ---
                if frame_id % 10 == 0:
                    try:
                        # import json # Moved to top
                        live_snapshot = {
                            "vehicle_count": len(objects),
                            "total_violations": len(total_unique_violations),
                            "queue_stats": queue_stats, # {'Lane 1': {'count': 5, ...}}
                            "total_queue": sum(q['count'] for q in queue_stats.values()),
                            "density": sum(q['count'] for q in queue_stats.values()) / max(1, len(queue_stats)),
                            "density": sum(q['count'] for q in queue_stats.values()) / max(1, len(queue_stats)),
                            "recent_violations": session_violations, # Send full list for dashboard expander
                            "class_distribution": class_counts # For live pie chart
                        }
                        
                        # Atomic write
                        temp_file = "data/live_stats.tmp"
                        with open(temp_file, 'w') as f:
                            json.dump(live_snapshot, f)
                        os.replace(temp_file, "data/live_stats.json")
                    except Exception:
                        pass # Don't crash main process for stats
    
                if frame_id % 10 == 0:
                    # Format lane stats string
                    lane_log = " | ".join([f"{k}: {v['count']}" for k, v in queue_stats.items()])
                    logging.info(f"Frame {frame_id} | Total: {len(objects)} | {lane_log}")
                    
        except KeyboardInterrupt:
            logging.info("Processing stopped by user.")
        finally:
            loader.close()
            out.release()
            cv2.destroyAllWindows()
            logging.info("Processing complete. Video saved.")
            
            # Save stats to CSV for dashboard
            import pandas as pd
            # Flatten stats for CSV
            flat_stats = []
            for s in all_stats:
                row = {
                    "frame": s["frame"],
                    "vehicle_count": s["vehicle_count"],
                    "violations": s["violations"]
                }
                # Add queue stats
                for lane, data in s["queue_stats"].items():
                    row[f"{lane}_count"] = data["count"]
                    row[f"{lane}_status"] = data["status"]
                flat_stats.append(row)
                
            df = pd.DataFrame(flat_stats)
            df.to_csv("data/stats.csv", index=False)
            logging.info("Stats saved to data/stats.csv")
    
            # Save Final Summary for accurate Dashboard reporting
            try:
                summary = {
                    "total_violations": len(total_unique_violations),
                    "vehicle_count": len(total_unique_ids),
                    "class_distribution": class_counts,
                    "queue_stats": queue_stats,
                    "density": sum(q['count'] for q in queue_stats.values()) / max(1, len(queue_stats)),
                    "recent_violations": session_violations
                }
                with open("data/final_summary.json", "w") as f:
                    json.dump(summary, f)
                logging.info("Final summary saved to data/final_summary.json")
            except Exception as e:
                logging.error(f"Failed to save summary: {e}")
                
    except Exception as e:
        # Retry logging
        logging.exception("FATAL ERROR IN MAIN PROCESS")
        raise e

if __name__ == "__main__":
    main()
