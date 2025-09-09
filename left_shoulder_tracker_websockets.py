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

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.pose_estimation_pipeline import GStreamerPoseEstimationApp


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

    user_data.set_detections(detections)
    return Gst.PadProbeReturn.OK


# ────────────────────────────────
#  Boilerplate app
# ────────────────────────────────
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.detections = []

    def set_frame(self, frame):      self.frame = frame
    def set_detections(self, dets):  self.detections = dets


if __name__ == "__main__":
    Gst.init(None)

    user_data = user_app_callback_class()
    app       = GStreamerPoseEstimationApp(app_callback, user_data)

    # Run in background
    threading.Thread(target=app.run, daemon=True).start()

    print("Tracking left shoulder... press Ctrl+C to stop.")
    try:
        while True:
            pass  # callback handles printing
    except KeyboardInterrupt:
        print("\nExiting.")
