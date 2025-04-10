import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import numpy as np
import pygame
import hailo
import threading

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.pose_estimation_pipeline import GStreamerPoseEstimationApp

# Initialize GStreamer
Gst.init(None)

# Pygame Setup
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720  # Adjust to match HDMI monitor resolution
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Motion Trails Visualization")
clock = pygame.time.Clock()

# Motion trail storage
trail_length = 30  # Number of points to keep for fading effect
left_wrist_trail = []
right_wrist_trail = []

# Colors
BACKGROUND_COLOR = (0, 0, 0)
LEFT_TRAIL_COLOR = (0, 255, 0)  # Green for left wrist
RIGHT_TRAIL_COLOR = (0, 0, 255)  # Blue for right wrist

# User-defined class for callback
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()

# GStreamer Callback Function
def app_callback(pad, info, user_data):
    global left_wrist_trail, right_wrist_trail

    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    user_data.increment()

    # Get detection results
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    keypoints = get_keypoints()

    for detection in detections:
        if detection.get_label() == "person":
            landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
            if len(landmarks) > 0:
                points = landmarks[0].get_points()

                # Extract wrist coordinates
                left_wrist_index = keypoints['left_wrist']
                right_wrist_index = keypoints['right_wrist']

                left_wrist = points[left_wrist_index]
                right_wrist = points[right_wrist_index]

                # Scale to screen size
                width, height = SCREEN_WIDTH, SCREEN_HEIGHT
                left_x, left_y = int(left_wrist.x() * width), int(left_wrist.y() * height)
                right_x, right_y = int(right_wrist.x() * width), int(right_wrist.y() * height)

                # Update trails
                update_trail(left_wrist_trail, (left_x, left_y))
                update_trail(right_wrist_trail, (right_x, right_y))

    return Gst.PadProbeReturn.OK

# Function to update trails
def update_trail(trail, new_point):
    trail.append(new_point)
    if len(trail) > trail_length:
        trail.pop(0)  # Remove oldest points to maintain trail length

# Get COCO keypoints
def get_keypoints():
    return {
        'nose': 0, 'left_eye': 1, 'right_eye': 2, 'left_ear': 3, 'right_ear': 4,
        'left_shoulder': 5, 'right_shoulder': 6, 'left_elbow': 7, 'right_elbow': 8,
        'left_wrist': 9, 'right_wrist': 10, 'left_hip': 11, 'right_hip': 12,
        'left_knee': 13, 'right_knee': 14, 'left_ankle': 15, 'right_ankle': 16,
    }

# Pygame Drawing Function
def draw_motion_trails():
    screen.fill(BACKGROUND_COLOR)

    # Draw fading trails
    draw_trail(left_wrist_trail, LEFT_TRAIL_COLOR)
    draw_trail(right_wrist_trail, RIGHT_TRAIL_COLOR)

    pygame.display.flip()

# Draw fading trail effect
def draw_trail(trail, color):
    if len(trail) < 2:
        return

    for i in range(len(trail) - 1):
        pygame.draw.line(screen, color, trail[i], trail[i + 1], 5)

# Main loop
def run_visualization():
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        draw_motion_trails()
        clock.tick(30)  # Ensure it runs at 30 FPS

        # Allow GStreamer to process frames
        pygame.display.flip()
        pygame.time.delay(1)  # Tiny delay to prevent CPU overuse

    pygame.quit()
    os._exit(0)  # Ensures Pygame properly exits without blocking GStreamer

# Main Execution
if __name__ == "__main__":
    user_data = user_app_callback_class()
    app = GStreamerPoseEstimationApp(app_callback, user_data)

    # Run GStreamer in a separate thread
    gst_thread = threading.Thread(target=app.run, daemon=True)
    gst_thread.start()

    # Run Pygame in the main loop
    run_visualization()
