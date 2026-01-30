import numpy as np
import cv2

def calculate_iou(box1, box2):
    """
    Calculate Intersection over Union (IoU) of two bounding boxes.
    Box format: [x1, y1, x2, y2]
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y1_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y2_1, y2_2)

    inter_width = max(0, xi2 - xi1)
    inter_height = max(0, yi2 - yi1)
    inter_area = inter_width * inter_height

    box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
    box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)

    union_area = box1_area + box2_area - inter_area
    
    if union_area == 0:
        return 0
    return inter_area / union_area

def calculate_iou_batch(bboxes1, bboxes2):
    """
    Calculate IoU between two sets of bounding boxes.
    bboxes1: (N, 4) numpy array [x1, y1, x2, y2]
    bboxes2: (M, 4) numpy array [x1, y1, x2, y2]
    Returns: (N, M) numpy array of IoU scores
    """
    if len(bboxes1) == 0 or len(bboxes2) == 0:
        return np.zeros((len(bboxes1), len(bboxes2)))
        
    bboxes1 = np.array(bboxes1)
    bboxes2 = np.array(bboxes2)
    
    # Expand dims for broadcasting
    # bboxes1: (N, 1, 4)
    # bboxes2: (1, M, 4)
    b1 = bboxes1[:, np.newaxis, :]
    b2 = bboxes2[np.newaxis, :, :]
    
    # Intersection coordinates
    xi1 = np.maximum(b1[..., 0], b2[..., 0])
    yi1 = np.maximum(b1[..., 1], b2[..., 1])
    xi2 = np.minimum(b1[..., 2], b2[..., 2])
    yi2 = np.minimum(b1[..., 3], b2[..., 3])
    
    inter_width = np.maximum(0, xi2 - xi1)
    inter_height = np.maximum(0, yi2 - yi1)
    inter_area = inter_width * inter_height
    
    # Union area
    box1_area = (b1[..., 2] - b1[..., 0]) * (b1[..., 3] - b1[..., 1])
    box2_area = (b2[..., 2] - b2[..., 0]) * (b2[..., 3] - b2[..., 1])
    union_area = box1_area + box2_area - inter_area
    
    # Avoid division by zero
    iou = np.zeros_like(inter_area, dtype=float)
    mask = union_area > 0
    iou[mask] = inter_area[mask] / union_area[mask]
    
    return iou

def point_in_polygon(point, polygon):
    """
    Check if a point (x, y) is inside a polygon (list of [x, y]).
    """
    # cv2.pointPolygonTest returns >0 if inside, 0 if on edge, <0 if outside
    # polygon must be numpy array of shape (N, 1, 2) or (N, 2)
    pts = np.array(polygon, dtype=np.int32)
    point = (int(point[0]), int(point[1]))
    dist = cv2.pointPolygonTest(pts, point, False)
    return dist >= 0

def get_centroid(bbox):
    """
    Returns (cx, cy) of a bbox [x1, y1, x2, y2].
    """
    x1, y1, x2, y2 = bbox
    return (int((x1 + x2) / 2), int((y1 + y2) / 2))

def ccw(A, B, C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

def segments_intersect(p1, p2, q1, q2):
    """
    Return True if segment p1-p2 intersects segment q1-q2.
    Points are (x, y) tuples or lists.
    """
    return ccw(p1, q1, q2) != ccw(p2, q1, q2) and ccw(p1, p2, q1) != ccw(p1, p2, q2)
