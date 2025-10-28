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
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = OUTPUT_DIR / f"multi_keypoint_{timestamp_str}.json"
CSV_FILE = OUTPUT_DIR / f"multi_keypoint_{timestamp_str}.csv"

# Data storage
tracking_data = []
start_time = time.time()
frame_count = 0

print(f"\n📁 Data will be saved to:")
print(f"   JSON: {OUTPUT_FILE}")
print(f"   CSV:  {CSV_FILE}\n")

# ────────────────────────────────
# PERFORMANCE CONFIGURATION
# ────────────────────────────────
# Print every Nth frame to reduce console overhead
PRINT_EVERY_N_FRAMES = 5  # Only print every 5th frame
print_counter = 0

# Keypoint indices mapping
KEYPOINTS = {
    5: "left_shoulder",
    6: "right_shoulder",
    7: "left_elbow",
    8: "right_elbow",
    9: "left_wrist",
    10: "right_wrist",
    11: "left_hip",
    12: "right_hip",
    13: "left_knee",
    14: "right_knee",
    15: "left_ankle",
    16: "right_ankle",
}

# ────────────────────────────────
#  GStreamer callback (OPTIMIZED)
# ────────────────────────────────
def app_callback(pad, info, user_data):
    global frame_count, print_counter
    
    buffer = info.get_buffer()
    if not buffer:
        return Gst.PadProbeReturn.OK

    user_data.increment()
    frame_count += 1
    print_counter += 1
    
    # Only process frame data every Nth frame to reduce overhead
    # But still do minimal processing for speed
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
    
    # Determine if we should print this frame
    should_print = (print_counter >= PRINT_EVERY_N_FRAMES)
    if should_print:
        print_counter = 0

    for idx, det in enumerate(detections):
        if det.get_label() != "person":
            continue
        lms = det.get_objects_typed(hailo.HAILO_LANDMARKS)
        if not lms:
            continue

        pts = lms[0].get_points()
        
        # Collect keypoints for this person
        person_keypoints = []
        
        # loop through defined keypoints
        for kp_idx, kp_name in KEYPOINTS.items():
            if len(pts) > kp_idx:
                kp = pts[kp_idx]
                x, y = kp.x(), kp.y()
                
                # Only print every Nth frame to reduce lag
                if should_print:
                    print(f"Person {idx}: {kp_name} at ({x:.3f}, {y:.3f})")
                
                # Store keypoint data
                person_keypoints.append({
                    "keypoint": kp_name,
                    "x": round(x, 4),
                    "y": round(y, 4)
                })
        
        # Store frame data (more efficient structure)
        if person_keypoints:
            tracking_data.append({
                "timestamp": timestamp,
                "elapsed_seconds": round(elapsed_time, 3),
                "frame": frame_count,
                "person_id": idx,
                "keypoints": person_keypoints
            })
    
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
        print(f"\n✓ Saved {len(tracking_data)} frames to JSON:")
        print(f"  {OUTPUT_FILE}")
    except Exception as e:
        print(f"\n✗ Failed to save JSON: {e}")
    
    # Save CSV (flattened format)
    try:
        with open(CSV_FILE, 'w') as f:
            # Write header
            f.write("timestamp,elapsed_seconds,frame,person_id,keypoint,x,y\n")
            # Write data
            for frame_data in tracking_data:
                for kp in frame_data['keypoints']:
                    f.write(f"{frame_data['timestamp']},{frame_data['elapsed_seconds']},"
                           f"{frame_data['frame']},{frame_data['person_id']},"
                           f"{kp['keypoint']},{kp['x']},{kp['y']}\n")
        print(f"✓ Saved data to CSV:")
        print(f"  {CSV_FILE}")
    except Exception as e:
        print(f"\n✗ Failed to save CSV: {e}")
    
    # Calculate statistics
    total_keypoints = sum(len(f['keypoints']) for f in tracking_data)
    duration = tracking_data[-1]['elapsed_seconds'] if tracking_data else 0
    
    print(f"\n📊 Summary:")
    print(f"   Total frames captured: {len(tracking_data)}")
    print(f"   Total keypoints: {total_keypoints}")
    print(f"   Duration: {duration:.1f} seconds")
    print(f"   Average FPS: {len(tracking_data)/duration:.1f}" if duration > 0 else "   Duration: N/A")
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

    print("Tracking keypoints (shoulders, elbows, wrists, hips, knees, ankles)...")
    print(f"⚡ Optimized: Printing every {PRINT_EVERY_N_FRAMES} frames to reduce lag")
    print("Press Ctrl+C to stop.\n")
    
    try:
        while True:
            pass  # callback handles printing
    except KeyboardInterrupt:
        print("\n\nStopping and saving data...")
        save_data()
        print("\nExiting.")