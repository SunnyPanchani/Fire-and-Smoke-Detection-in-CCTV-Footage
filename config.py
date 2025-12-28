# config.py - Global configuration and constants
import os
import sys
from collections import deque

def get_base_dir():
    """Get base directory for files"""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

# Base directories and paths
BASE_DIR = get_base_dir()
ALERTS_DIR = os.path.join(BASE_DIR, "alerts")

# Ensure alerts directory exists
os.makedirs(ALERTS_DIR, exist_ok=True)

# Model paths
FIRE_MODEL_PATH = os.path.join(BASE_DIR, "lumi.onnx")
# FIRE_MODEL_PATH = os.path.join(BASE_DIR, "best_epoch_140.pt")
PERSON_MODEL_PATH = os.path.join(BASE_DIR, "person.onnx")

# File size limits
ALERTS_FOLDER_MAX_SIZE = 5 * 1024 * 1024  # 5MB
LOG_FILE_MAX_SIZE = 1 * 1024 * 1024  # 1MB

# Screen and Device Classes for Smart Filtering
SCREEN_DEVICE_CLASSES = {
    62: 'tv',           # Television
    63: 'laptop',       # Laptop computer
    67: 'cell phone',   # Mobile phone/smartphone
    64: 'mouse',        # Computer mouse (often near screens)
    65: 'remote',       # TV remote (indicates TV presence)
    66: 'keyboard'      # Keyboard (indicates computer setup)
}

# Electronic devices that could catch fire but might also show content
ELECTRONIC_DEVICE_CLASSES = {
    68: 'microwave',    # Microwave oven
    69: 'oven',         # Oven
    70: 'toaster',      # Toaster
    72: 'refrigerator', # Refrigerator
    75: 'vase',         # Could be electronic
    76: 'scissors',     # Metal objects
    78: 'hair drier',   # Hair dryer
    79: 'toothbrush'    # Electric toothbrush
}

# All 80 COCO classes that could potentially interfere with fire detection
ALL_INTERFERENCE_CLASSES = {
    0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane', 5: 'bus',
    6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light', 10: 'fire hydrant',
    11: 'stop sign', 12: 'parking meter', 13: 'bench', 14: 'bird', 15: 'cat',
    16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow', 20: 'elephant', 21: 'bear',
    22: 'zebra', 23: 'giraffe', 24: 'backpack', 25: 'umbrella', 26: 'handbag',
    27: 'tie', 28: 'suitcase', 29: 'frisbee', 30: 'skis', 31: 'snowboard',
    32: 'sports ball', 33: 'kite', 34: 'baseball bat', 35: 'baseball glove',
    36: 'skateboard', 37: 'surfboard', 38: 'tennis racket', 39: 'bottle',
    40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife', 44: 'spoon', 45: 'bowl',
    46: 'banana', 47: 'apple', 48: 'sandwich', 49: 'orange', 50: 'broccoli',
    51: 'carrot', 52: 'hot dog', 53: 'pizza', 54: 'donut', 55: 'cake',
    56: 'chair', 57: 'couch', 58: 'potted plant', 59: 'bed', 60: 'dining table',
    61: 'toilet', 62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote', 66: 'keyboard',
    67: 'cell phone', 68: 'microwave', 69: 'oven', 70: 'toaster', 71: 'sink',
    72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase', 76: 'scissors',
    77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'
}

# Alert timing constants
FIRE_ALERT_COOLDOWN = 180  # 3 minutes for fire
SMOKE_ALERT_COOLDOWN = 300  # 5 minutes for smoke (longer due to strict detection)
NOTIFICATION_INTERVAL = 900  # 15 minutes for startup notifications

# Detection statistics
DETECTION_STATS = {
    'fire_detections': 0,
    'smoke_detections': 0,
    'valid_fire_detections': 0,
    'valid_smoke_detections': 0,
    'false_positives_avoided': 0,
    'objects_excluded_detections': 0,
    'total_frames': 0,
    'fire_alerts_sent': 0,
    'smoke_alerts_sent': 0,
    'last_fire_time': 0,
    'last_smoke_time': 0
}

# Internet monitoring state
INTERNET_MONITOR_STATE = {
    "is_connected": False,
    "last_check_time": 0,
    "total_outages": 0,
    "short_outages_count": 0,
    "significant_outages_count": 0,
    "outage_start_time": None,
    "last_outage_duration": 0,
    "longest_outage_seconds": 0,
    "total_downtime_seconds": 0
}

# Global tracking variables
LAST_FIRE_DETECTION_IMAGE = None
LAST_NOTIFICATION_TIME = None
LAST_FIRE_ALERT_TIME = {}
LAST_SMOKE_ALERT_TIME = {}

# Model instances (to be initialized)
FIRE_MODEL = None
PERSON_MODEL = None

# Global detectors
ADAPTIVE_DETECTORS = {}
BRIGHTNESS_DETECTORS = {}