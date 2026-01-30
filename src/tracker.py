from collections import OrderedDict
import numpy as np
from .utils import get_centroid

class SimpleTracker:
    """
    A simple centroid-based object tracker.
    Assigns IDs to objects based on Euclidean distance between centroids in consecutive frames.
    """
    def __init__(self, max_disappeared=30, max_distance=50):
        """
        Args:
            max_disappeared: Number of frames to keep an object ID after it's lost.
            max_distance: Maximum pixel distance to associate an object.
        """
        self.next_object_id = 0
        self.objects = OrderedDict()  # object_id -> centroid (x, y)
        self.disappeared = OrderedDict() # object_id -> frames_since_seen
        self.bboxes = OrderedDict() # object_id -> bbox [x1, y1, x2, y2]
        self.classes = OrderedDict() # object_id -> class_name
        self.history = OrderedDict() # object_id -> list of centroids (for trajectory)
        
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid, bbox, class_name):
        self.objects[self.next_object_id] = centroid
        self.bboxes[self.next_object_id] = bbox
        self.classes[self.next_object_id] = class_name
        self.disappeared[self.next_object_id] = 0
        self.history[self.next_object_id] = [centroid]
        self.next_object_id += 1

    def deregister(self, object_id):
        del self.objects[object_id]
        del self.disappeared[object_id]
        del self.bboxes[object_id]
        del self.classes[object_id]
        del self.history[object_id]

    def update(self, detections):
        """
        Args:
            detections: List of dicts with 'bbox' and 'class_name' keys.
        Returns:
            objects: Dictionary of object_id -> centroid
        """
        # Extract centroids from detections
        input_centroids = np.zeros((len(detections), 2), dtype="int")
        input_bboxes = []
        input_classes = []
        
        for i, d in enumerate(detections):
            input_centroids[i] = get_centroid(d['bbox'])
            input_bboxes.append(d['bbox'])
            input_classes.append(d['class_name'])

        # If no objects are currently tracked
        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self.register(input_centroids[i], input_bboxes[i], input_classes[i])
        
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            # Calculate IoU matrix
            # IoU[i, j] is IoU between object i and detection j
            from .utils import calculate_iou_batch
            
            obj_bboxes = list(self.bboxes.values())
            iou_matrix = calculate_iou_batch(obj_bboxes, input_bboxes)
            
            # Find matches with highest IoU
            # We want to maximize total IoU, but greedy is fine for simple tracking
            
            # Sort by IoU descending
            if iou_matrix.size > 0:
                # Flatten and sort indices
                flat_indices = np.argsort(iou_matrix, axis=None)[::-1]
                
                used_rows = set()
                used_cols = set()
                
                for idx in flat_indices:
                    row, col = np.unravel_index(idx, iou_matrix.shape)
                    
                    if row in used_rows or col in used_cols:
                        continue
                        
                    # If IoU is too low, don't associate
                    if iou_matrix[row, col] < 0.1: # Threshold 0.1
                        continue
                        
                    object_id = object_ids[row]
                    self.objects[object_id] = input_centroids[col]
                    self.bboxes[object_id] = input_bboxes[col]
                    self.classes[object_id] = input_classes[col]
                    self.disappeared[object_id] = 0
                    self.history[object_id].append(input_centroids[col])
                    
                    if len(self.history[object_id]) > 20:
                        self.history[object_id].pop(0)
                        
                    used_rows.add(row)
                    used_cols.add(col)
            else:
                used_rows = set()
                used_cols = set()

            # Compute rows and cols that we haven't examined
            unused_rows = set(range(0, iou_matrix.shape[0])).difference(used_rows)
            unused_cols = set(range(0, iou_matrix.shape[1])).difference(used_cols)

            # Handle disappeared objects
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            # Register new objects
            for col in unused_cols:
                self.register(input_centroids[col], input_bboxes[col], input_classes[col])

        return self.objects
