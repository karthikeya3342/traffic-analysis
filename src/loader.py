import cv2
import time
from typing import Generator, Tuple, Optional
import logging

class VideoLoader:
    """
    Handles video loading, resizing, and frame iteration.
    """
    def __init__(self, video_path: str, resize_dim: Optional[Tuple[int, int]] = None):
        """
        Args:
            video_path: Path to the input video file.
            resize_dim: Tuple (width, height) to resize frames to. None to keep original.
        """
        self.video_path = video_path
        self.resize_dim = resize_dim
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
            
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if self.resize_dim:
            self.width, self.height = self.resize_dim

        logging.info(f"Video loaded: {video_path} | FPS: {self.fps} | Resolution: {self.width}x{self.height}")

    def __iter__(self) -> Generator[Tuple[int, object], None, None]:
        """
        Yields:
            frame_id (int): The current frame number.
            frame (numpy.ndarray): The video frame.
        """
        frame_id = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            if self.resize_dim:
                frame = cv2.resize(frame, self.resize_dim)
                
            yield frame_id, frame
            frame_id += 1
            
    def close(self):
        self.cap.release()

if __name__ == "__main__":
    # Test the loader
    try:
        loader = VideoLoader("data/sample_video.mp4", resize_dim=(640, 360))
        for fid, frame in loader:
            print(f"Frame {fid} shape: {frame.shape}")
            if fid > 5: break
        loader.close()
    except Exception as e:
        print(f"Loader test skipped/failed: {e}")
