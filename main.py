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
import time
from pythonosc import udp_client

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.pose_estimation_pipeline import GStreamerPoseEstimationApp

# ────────────────────────────────
# CONFIGURATION
# ────────────────────────────────
# Prompt user for IP addresses
print("\n" + "="*60)
print("Pose Estimation Setup")
print("="*60)

ISADORA_IP = input("Enter Isadora IP address: ").strip()
use_same_ip = input("Use same IP for OSC? (Y/n): ").strip().lower()

if use_same_ip == 'n' or use_same_ip == 'no':
    OSC_IP = input("Enter OSC IP address: ").strip()
else:
    OSC_IP = ISADORA_IP
    print(f"Using {OSC_IP} for OSC")

# Default ports
ISADORA_PORT = 8765
OSC_PORT = 1234

# Coordinate scaling configuration
COORD_MIN = 0
COORD_MAX = 600

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

# Timing control for 0.5 second delay
last_send_time = 0
SEND_DELAY = 0.5  # seconds


# ────────────────────────────────
#  Coordinate scaling function
# ────────────────────────────────
def scale_coordinate(value, min_val=COORD_MIN, max_val=COORD_MAX):
    """
    Scale normalized coordinate (0.0-1.0) to desired range (default 0-600)
    Returns rounded to 2 decimal places
    """
    scaled = min_val + (value * (max_val - min_val))
    return round(scaled, 2)


# ────────────────────────────────
#  GStreamer callback
# ────────────────────────────────
def app_callback(pad, info, user_data):
    """Process each frame and extract keypoint data"""
    global last_send_time
    
    # Check if enough time has passed since last send
    current_time = time.time()
    if current_time - last_send_time < SEND_DELAY:
        return Gst.PadProbeReturn.OK
    
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
            if kp_idx < len(pts):
                kp = pts[kp_idx]
                x_raw, y_raw = kp.x(), kp.y()
                
                # Scale coordinates to 0-600 range and round to 2 decimals
                x_scaled = scale_coordinate(x_raw)
                y_scaled = scale_coordinate(y_raw)
                
                # Add to WebSocket data (scaled and rounded)
                person_data['keypoints'].append({
                    'label': kp_name,
                    'x': x_scaled,
                    'y': y_scaled
                })
                
                # Add to OSC data if in OSC keypoint list (scaled and rounded)
                if kp_name in OSC_KEYPOINTS:
                    list_x[f"{kp_name}/p{idx + 1}"] = x_scaled
                    list_y[f"{kp_name}/p{idx + 1}"] = y_scaled
                
                # Print for debugging (only if data is being sent)
                print(f"Person {idx + 1}: {kp_name} at ({x_scaled:.2f}, {y_scaled:.2f})")

        if person_data['keypoints']:  # Only add if keypoints were found
            coordinates_data.append(person_data)

    # Update last send time if we have data to send
    if coordinates_data or (list_x and list_y):
        last_send_time = current_time

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
                        json_data = json.dumps(data)
                        await websocket.send(json_data)
                        print(f"✓ Sent WebSocket data for {len(data)} person(s) - {len(json_data)} bytes")
                    except Exception as e:
                        print(f"✗ Failed to send WebSocket data: {e}")
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
    sent_count = 0
    for (key1, value1), (key2, value2) in zip(x_list.items(), y_list.items()):
        channel_x = f"{address_x}/{key1}"
        channel_y = f"{address_y}/{key2}"
        
        try:
            osc_client.send_message(channel_x, value1)
            osc_client.send_message(channel_y, value2)
            sent_count += 1
            print(f"OSC: {channel_x} = {value1:.2f}, {channel_y} = {value2:.2f}")
        except Exception as e:
            print(f"✗ OSC send error for {key1}: {e}")
    
    if sent_count > 0:
        print(f"✓ Sent {sent_count} OSC keypoint pairs")


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
    print(f"Coordinate range: {COORD_MIN}-{COORD_MAX}")
    print(f"Decimal precision: 2 places")
    print(f"Send delay: {SEND_DELAY} seconds")
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
