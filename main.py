
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
import websockets
import asyncio
import json
from pythonosc import udp_client

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.pose_estimation_pipeline import GStreamerPoseEstimationApp

# ────────────────────────────────
# CONFIGURATION - EDIT THESE VALUES
# ────────────────────────────────
# OSC Configuration (for local Isadora instance if running on Pi)
OSC_IP = "10.186.117.84"
OSC_PORT = 1234

# WebSocket Configuration (to send to laptop running Isadora)
ISADORA_IP = "10.186.117.84"  # REPLACE WITH YOUR LAPTOP'S IP ADDRESS
ISADORA_PORT = 8765

# Keypoints to track (COCO format indices and names)
KEYPOINTS = {
    0: 'nose',
    1: 'left_eye',
    2: 'right_eye',
    3: 'left_ear',
    4: 'right_ear',
    5: 'left_shoulder',
    6: 'right_shoulder',
    7: 'left_elbow',
    8: 'right_elbow',
    9: 'left_wrist',
    10: 'right_wrist',
    11: 'left_hip',
    12: 'right_hip',
    13: 'left_knee',
    14: 'right_knee',
    15: 'left_ankle',
    16: 'right_ankle'
}

# Keypoints to send via OSC (subset of all keypoints)
OSC_KEYPOINTS = ['left_shoulder', 'right_shoulder', 'left_wrist', 'right_wrist']
# ────────────────────────────────

# Set up OSC client
osc_client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)
address_x = "/isadora-multi/1"
address_y = "/isadora-multi/2"

# Global event loop and queue for websockets
loop = None
websocket_queue = asyncio.Queue()

# ────────────────────────────────
#  GStreamer callback
# ────────────────────────────────
def app_callback(pad, info, user_data):
    """Process each frame and extract keypoint data"""
    coordinates_data = []
    list_x = {}
    list_y = {}

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
        
        # Prepare person data structure
        person_data = {
            'person': idx + 1,
            'keypoints': []
        }

        # Loop through all defined keypoints
        for kp_idx, kp_name in KEYPOINTS.items():
            if len(pts) > kp_idx:
                kp = pts[kp_idx]
                x, y = kp.x(), kp.y()
                
                # Add to WebSocket data
                person_data['keypoints'].append({
                    'label': kp_name,
                    'x': float(x),
                    'y': float(y)
                })
                
                # Add to OSC data if in OSC keypoint list
                if kp_name in OSC_KEYPOINTS:
                    list_x[f"{kp_name}/p{idx + 1}"] = float(x)
                    list_y[f"{kp_name}/p{idx + 1}"] = float(y)
                
                # Print for debugging
                print(f"Person {idx + 1}: {kp_name} at ({x:.3f}, {y:.3f})")

        coordinates_data.append(person_data)

    # Send data via WebSocket (queued for async processing)
    if coordinates_data and loop:
        asyncio.run_coroutine_threadsafe(
            websocket_queue.put(coordinates_data), loop
        )
    
    # Send data via OSC (immediate)
    if list_x and list_y:
        send_osc(list_x, list_y)
    
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

    def set_frame(self, frame):
        self.frame = frame
        
    def set_detections(self, dets):
        self.detections = dets


# ────────────────────────────────
#  WebSocket sender
# ────────────────────────────────
async def websocket_sender():
    """Background task to send websocket data"""
    reconnect_delay = 1.0
    max_reconnect_delay = 30.0
    
    while True:
        try:
            uri = f"ws://{ISADORA_IP}:{ISADORA_PORT}"
            print(f"Connecting to WebSocket server at {uri}...")
            
            async with websockets.connect(uri, ping_timeout=20, ping_interval=10) as websocket:
                print("✓ Connected to WebSocket server")
                reconnect_delay = 1.0  # Reset delay on successful connection
                
                while True:
                    # Wait for data to be queued
                    data = await websocket_queue.get()
                    
                    try:
                        await websocket.send(json.dumps(data))
                        print(f"✓ Sent data for {len(data)} person(s)")
                    except Exception as e:
                        print(f"✗ Failed to send data: {e}")
                        break  # Break inner loop to reconnect
                        
        except Exception as e:
            print(f"✗ WebSocket connection error: {e}")
            print(f"  Retrying in {reconnect_delay:.1f} seconds...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)


# ────────────────────────────────
#  OSC sender
# ────────────────────────────────
def send_osc(x_list, y_list):
    """Send keypoint data via OSC"""
    for (key1, value1), (key2, value2) in zip(x_list.items(), y_list.items()):
        channel_x = f"{address_x}/{key1}"
        channel_y = f"{address_y}/{key2}"
        
        try:
            osc_client.send_message(channel_x, value1)
            osc_client.send_message(channel_y, value2)
            print(f"OSC: {channel_x} = {value1:.3f}, {channel_y} = {value2:.3f}")
        except Exception as e:
            print(f"✗ OSC send error: {e}")


# ────────────────────────────────
#  Main async loop
# ────────────────────────────────
async def main():
    global loop
    loop = asyncio.get_running_loop()
    
    # Start the websocket sender task
    websocket_task = asyncio.create_task(websocket_sender())
    
    print("\n" + "="*60)
    print("Pose Estimation with WebSocket & OSC")
    print("="*60)
    print(f"WebSocket target: ws://{ISADORA_IP}:{ISADORA_PORT}")
    print(f"OSC target: {OSC_IP}:{OSC_PORT}")
    print(f"Tracking {len(KEYPOINTS)} keypoints")
    print(f"OSC keypoints: {', '.join(OSC_KEYPOINTS)}")
    print("="*60)
    print("\nPress Ctrl+C to stop.\n")
    
    try:
        # Keep the async loop running
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("\n\nExiting...")
        websocket_task.cancel()


if __name__ == "__main__":
    Gst.init(None)

    user_data = user_app_callback_class()
    app = GStreamerPoseEstimationApp(app_callback, user_data)

    # Run GStreamer in background thread
    threading.Thread(target=app.run, daemon=True).start()

    # Run the async websocket handler
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
