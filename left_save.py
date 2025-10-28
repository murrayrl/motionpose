#!/usr/bin/env python3
import sys
sys.path.append("/home/mlm/JG_POSE/hailo-apps-infra")
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
import threading
import cv2
import numpy as np
import hailo
import json
import time
from datetime import datetime
from pathlib import Path

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.pose_estimation_pipeline import GStreamerPoseEstimationApp

# ────────────────────────────────
# FILE LOGGING CONFIGURATION
# ────────────────────────────────
OUTPUT_DIR = Path.home() / "pose_data"  # Saves to /home/mlm/pose_data
OUTPUT_DIR.mkdir(exist_ok=True)

# Generate filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = OUTPUT_DIR / f"left_shoulder_{timestamp}.json"
CSV_FILE = OUTPUT_DIR / f"left_shoulder_{timestamp}.csv"

# Data storage
tracking_data = []
start_time = time.time()

print(f"\n📁 Data will be saved to:")
print(f"   JSON: {OUTPUT_FILE}")
print(f"   CSV:  {CSV_FILE}\n")

# ────────────────────────────────
#  GStreamer callback
# ────────────────────────────────
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if not buffer:
        return Gst.PadProbeReturn.OK

    user_data.increment()
    fmt, w, h = get_caps_from_pad(pad)
    if fmt and w and h:
        frame = get_numpy_from_buffer(buffer, fmt, w, h)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # Get current timestamp
    elapsed_time = time.time() - start_time
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    for idx, det in enumerate(detections):
        if det.get_label() != "person":
            continue
        lms = det.get_objects_typed(hailo.HAILO_LANDMARKS)
        if not lms:
            continue

        pts = lms[0].get_points()
        
        # left shoulder is index 5 in keypoints
        if len(pts) > 5:
            left_shoulder = pts[5]
            x, y = left_shoulder.x(), left_shoulder.y()
            print(f"Person {idx}: Left shoulder at ({x:.3f}, {y:.3f})")
            
            # Store data for logging
            data_point = {
                "timestamp": timestamp,
                "elapsed_seconds": round(elapsed_time, 3),
                "person_id": idx,
                "keypoint": "left_shoulder",
                "x": round(x, 4),
                "y": round(y, 4)
            }
            tracking_data.append(data_point)

    user_data.set_detections(detections)
    return Gst.PadProbeReturn.OK

# ────────────────────────────────
#  Save data functions
# ────────────────────────────────
def save_data():
    """Save collected data to JSON and CSV files"""
    if not tracking_data:
        print("\n⚠️  No data collected to save")
        return
    
    # Save JSON
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(tracking_data, f, indent=2)
        print(f"\n✓ Saved {len(tracking_data)} data points to JSON:")
        print(f"  {OUTPUT_FILE}")
    except Exception as e:
        print(f"\n✗ Failed to save JSON: {e}")
    
    # Save CSV
    try:
        with open(CSV_FILE, 'w') as f:
            # Write header
            f.write("timestamp,elapsed_seconds,person_id,keypoint,x,y\n")
            # Write data
            for point in tracking_data:
                f.write(f"{point['timestamp']},{point['elapsed_seconds']},"
                       f"{point['person_id']},{point['keypoint']},"
                       f"{point['x']},{point['y']}\n")
        print(f"✓ Saved {len(tracking_data)} data points to CSV:")
        print(f"  {CSV_FILE}")
    except Exception as e:
        print(f"\n✗ Failed to save CSV: {e}")
    
    print(f"\n📊 Summary:")
    print(f"   Total frames: {len(tracking_data)}")
    print(f"   Duration: {tracking_data[-1]['elapsed_seconds']:.1f} seconds")
    print(f"   Location: {OUTPUT_DIR}")

# ────────────────────────────────
#  Boilerplate app
# ────────────────────────────────
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.detections = []
    
    def set_frame(self, frame):
        self.frame = frame
    
    def set_detections(self, dets):
        self.detections = dets

if __name__ == "__main__":
    Gst.init(None)

    user_data = user_app_callback_class()
    app = GStreamerPoseEstimationApp(app_callback, user_data)

    # Run in background
    threading.Thread(target=app.run, daemon=True).start()

    print("Tracking left shoulder... press Ctrl+C to stop.")
    try:
        while True:
            pass  # callback handles printing
    except KeyboardInterrupt:
        print("\n\nStopping and saving data...")
        save_data()
        print("\nExiting.")