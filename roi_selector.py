import cv2
import yaml
import argparse

# Global variables to store points
points = []

def click_event(event, x, y, flags, params):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        print(f"Clicked: [{x}, {y}]")
        cv2.circle(params['image'], (x, y), 5, (0, 0, 255), -1)
        cv2.imshow("ROI Selector", params['image'])

def select_rois(video_path):
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print(f"Failed to read video: {video_path}")
        return

    # Resize to match config processing size (default 1280x720)
    frame = cv2.resize(frame, (1280, 720))
    
    print("\n--- ROI Selector ---")
    print("1. Click points to define a polygon (Lane) or Line (Stop Line).")
    print("2. Press 'c' to clear points.")
    print("3. Press 'p' to print the current list of points (copy this to config.yaml).")
    print("4. Press 'q' to quit.")
    
    cv2.imshow("ROI Selector", frame)
    cv2.setMouseCallback("ROI Selector", click_event, {'image': frame})
    
    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            points.clear()
            # Reload frame to clear circles
            clean_frame = frame.copy()
            cv2.imshow("ROI Selector", clean_frame)
            cv2.setMouseCallback("ROI Selector", click_event, {'image': clean_frame})
            print("Cleared points.")
        elif key == ord('p'):
            print(f"\nCaptured Points: {points}")
            print("Copy the above list to your config.yaml under 'queue_rois' or 'stop_line'.\n")

    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path", help="Path to the video file")
    args = parser.parse_args()
    
    select_rois(args.video_path)
