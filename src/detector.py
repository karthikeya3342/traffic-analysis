from abc import ABC, abstractmethod
import numpy as np
import cv2
from typing import List, Dict, Any
import logging

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

class TrafficDetector(ABC):
    """
    Abstract base class for traffic detectors.
    """
    @abstractmethod
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Args:
            frame: Input image (BGR).
        Returns:
            List of detections. Each detection is a dict:
            {
                'bbox': [x1, y1, x2, y2],
                'class_id': int,
                'class_name': str,
                'confidence': float
            }
        """
        pass

class MockDetector(TrafficDetector):
    """
    Returns random detections for testing without a model.
    """
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        # Simulate a car moving across the screen
        import random
        detections = []
        # Create 3 fake cars
        for i in range(3):
            x = random.randint(0, self.width - 100)
            y = random.randint(200, self.height - 100)
            w, h = 100, 60
            detections.append({
                'bbox': [x, y, x+w, y+h],
                'class_id': 2,
                'class_name': 'car',
                'confidence': 0.95,
                'track_id': i
            })
        return detections

class YoloDetector(TrafficDetector):
    """
    YOLOv8 based detector.
    """
    def __init__(self, model_path: str = "yolov8n.pt", conf_thres: float = 0.3, classes: List[int] = None):
        if YOLO is None:
            raise ImportError("ultralytics not installed. Run `pip install ultralytics`.")
        
        logging.info(f"Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)
        self.conf_thres = conf_thres
        self.classes = classes # COCO classes filter
        
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        # Use model.track instead of model.predict to get built-in tracking
        results = self.model.track(frame, conf=self.conf_thres, classes=self.classes, persist=True, verbose=False)
        detections = []
        
        for r in results:
            boxes = r.boxes
            if boxes is None:
                continue
                
            for box in boxes:
                # Check if we have track IDs
                if box.id is None:
                    continue
                    
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                track_id = int(box.id[0].cpu().numpy())
                cls_name = self.model.names[cls_id]
                
                detections.append({
                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                    'class_id': cls_id,
                    'class_name': cls_name,
                    'confidence': conf,
                    'track_id': track_id
                })
        return detections
