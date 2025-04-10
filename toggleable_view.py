import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import numpy as np
import pygame
import hailo
import threading
import cv2

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
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720  # HDMI resolution
HALF_SCREEN_WIDTH = SCREEN_WIDTH // 2
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Toggleable Visualization")

clock = pygame.time.Clock()

# Motion trail storage
trail_length = 30
left_wrist_trail = []
right_wrist_trail = []

# Colors
BACKGROUND_COLOR = (0, 0, 0)
LEFT_TRAIL_COLOR = (0, 255, 0)
RIGHT_TRAIL_COLOR = (0, 0, 255)
BBOX_COLOR = (255, 255, 0)

# Screen state
screen_state = 0  # 0: Motion Trails, 1: Keypoints + BBox, 2: Split Screen

# User-defined class for callback
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.frame = None  # Store latest camera frame
        self.detections = []

    def set_frame(self, frame):
        self.frame = frame

    def set_detections(self, detections):
        self.detections = detections

# GStreamer Callback Function
def app_callback(pad, info, user_data):
    global left_wrist_trail, right_wrist_trail

    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    user_data.increment()
    format, width, height = get_caps_from_pad(pad)

    frame = None
    if format is not None and width is not None and height is not None:
        frame = get_numpy_from_buffer(buffer, format, width, height)

    if frame is not None:
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convert for OpenCV
        user_data.set_frame(frame)

    # Get detection results
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    user_data.set_detections(detections)

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

                # Scale to screen size (left half)
                left_x, left_y = int(left_wrist.x() * HALF_SCREEN_WIDTH), int(left_wrist.y() * SCREEN_HEIGHT)
                right_x, right_y = int(right_wrist.x() * HALF_SCREEN_WIDTH), int(right_wrist.y() * SCREEN_HEIGHT)

                # Update trails
                update_trail(left_wrist_trail, (left_x, left_y))
                update_trail(right_wrist_trail, (right_x, right_y))

    return Gst.PadProbeReturn.OK

# Function to update trails
def update_trail(trail, new_point):
    trail.append(new_point)
    if len(trail) > trail_length:
        trail.pop(0)

# Get COCO keypoints
def get_keypoints():
    return {
        'nose': 0, 'left_eye': 1, 'right_eye': 2, 'left_ear': 3, 'right_ear': 4,
        'left_shoulder': 5, 'right_shoulder': 6, 'left_elbow': 7, 'right_elbow': 8,
        'left_wrist': 9, 'right_wrist': 10, 'left_hip': 11, 'right_hip': 12,
        'left_knee': 13, 'right_knee': 14, 'left_ankle': 15, 'right_ankle': 16,
    }

# Pygame Drawing Functions
def draw_motion_trails():
    screen.fill(BACKGROUND_COLOR)
    draw_trail(left_wrist_trail, LEFT_TRAIL_COLOR)
    draw_trail(right_wrist_trail, RIGHT_TRAIL_COLOR)

def draw_trail(trail, color):
    if len(trail) < 2:
        return

    for i in range(len(trail) - 1):
        x1, y1 = trail[i]
        x2, y2 = trail[i + 1]
        pygame.draw.line(screen, color, (x1, y1), (x2, y2), 5)

# Draw bounding boxes and keypoints
def draw_keypoints_and_bbox(user_data):
    if user_data.frame is not None:
        frame = cv2.resize(user_data.frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
        frame = np.rot90(frame)
        frame = pygame.surfarray.make_surface(frame)
        screen.blit(frame, (0, 0))

        for detection in user_data.detections:
            if detection.get_label() == "person":
                bbox = detection.get_bbox()
                x1, y1, x2, y2 = (
                    int(bbox.xmin() * SCREEN_WIDTH),
                    int(bbox.ymin() * SCREEN_HEIGHT),
                    int(bbox.xmax() * SCREEN_WIDTH),
                    int(bbox.ymax() * SCREEN_HEIGHT),
                )
                pygame.draw.rect(screen, BBOX_COLOR, (x1, y1, x2 - x1, y2 - y1), 2)

# Draw split-screen visualization
def draw_split_screen(user_data):
    screen.fill(BACKGROUND_COLOR)

    # Left side: Motion trails
    draw_trail(left_wrist_trail, LEFT_TRAIL_COLOR)
    draw_trail(right_wrist_trail, RIGHT_TRAIL_COLOR)

    # Right side: Keypoints & Bounding Boxes
    if user_data.frame is not None:
        frame = cv2.resize(user_data.frame, (HALF_SCREEN_WIDTH, SCREEN_HEIGHT))
        frame = np.rot90(frame)
        frame = pygame.surfarray.make_surface(frame)
        screen.blit(frame, (HALF_SCREEN_WIDTH, 0))

        for detection in user_data.detections:
            if detection.get_label() == "person":
                bbox = detection.get_bbox()
                x1, y1, x2, y2 = (
                    int(bbox.xmin() * HALF_SCREEN_WIDTH) + HALF_SCREEN_WIDTH,
                    int(bbox.ymin() * SCREEN_HEIGHT),
                    int(bbox.xmax() * HALF_SCREEN_WIDTH) + HALF_SCREEN_WIDTH,
                    int(bbox.ymax() * SCREEN_HEIGHT),
                )
                pygame.draw.rect(screen, BBOX_COLOR, (x1, y1, x2 - x1, y2 - y1), 2)

# Main loop
def run_visualization(user_data):
    global screen_state
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    screen_state = (screen_state + 1) % 3
                elif event.key == pygame.K_LEFT:
                    screen_state = (screen_state - 1) % 3

        if screen_state == 0:
            draw_motion_trails()
        elif screen_state == 1:
            draw_keypoints_and_bbox(user_data)
        elif screen_state == 2:
            draw_split_screen(user_data)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    os._exit(0)  # Ensures clean exit

# Main Execution
if __name__ == "__main__":
    user_data = user_app_callback_class()
    app = GStreamerPoseEstimationApp(app_callback, user_data)

    gst_thread = threading.Thread(target=app.run, daemon=True)
    gst_thread.start()

    run_visualization(user_data)
