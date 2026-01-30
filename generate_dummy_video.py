import cv2
import numpy as np

def create_dummy_video(filename="data/sample_video.mp4", duration=5, fps=30, width=1280, height=720):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    
    frames = duration * fps
    
    # Vehicle positions (x, y)
    car1_y = 200
    car2_y = 300
    
    for i in range(frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Draw road
        cv2.rectangle(frame, (0, 0), (width, height), (50, 50, 50), -1)
        
        # Draw lanes
        cv2.line(frame, (400, 0), (400, height), (255, 255, 255), 2)
        cv2.line(frame, (800, 0), (800, height), (255, 255, 255), 2)
        
        # Move cars
        car1_y += 5
        car2_y += 3
        
        if car1_y > height: car1_y = 0
        if car2_y > height: car2_y = 0
        
        # Draw cars
        cv2.rectangle(frame, (200, car1_y), (300, car1_y + 60), (0, 255, 0), -1)
        cv2.rectangle(frame, (600, car2_y), (700, car2_y + 80), (0, 0, 255), -1)
        
        out.write(frame)
        
    out.release()
    print(f"Created dummy video: {filename}")

if __name__ == "__main__":
    create_dummy_video()
