import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import os
import numpy as np
import pygame
import hailo
import threading
import cv2
import importlib.util

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from hailo_apps_infra.pose_estimation_pipeline import GStreamerPoseEstimationApp

# Initialize GStreamer and Pygame
Gst.init(None)
pygame.init()
pygame.mixer.init()  # For audio
SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
HALF_SCREEN_WIDTH = SCREEN_WIDTH // 2
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Enhanced Pose Estimation with Audio")

clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)

# Colors
BACKGROUND_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 255)
BBOX_COLOR = (255, 255, 0)
KEYPOINT_COLOR = (255, 0, 0)

# Visualization settings
visuals = []
visual_names = []
sounds = []
current_visual_index = 0
screen_state = 0  # 0: Visual only, 1: Split-screen, 2: Camera with keypoints & bbox
confidence_threshold = 0.5
show_keypoints = True
current_sound = None

# Load visuals and sounds
def load_visuals():
    visuals_dir = "multi_person_visuals"
    sounds_dir = "sounds"
    if os.path.exists(visuals_dir):
        for file in os.listdir(visuals_dir):
            if file.endswith(".py"):
                module_name = file[:-3]
                module_path = os.path.join(visuals_dir, file)
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "VisualClass"):
                    visual_instance = module.VisualClass()
                    visuals.append(visual_instance)
                    visual_names.append(module_name.replace("_", " ").title())
                    sound_file = os.path.join(sounds_dir, module_name + ".wav")
                    if os.path.exists(sound_file):
                        sound = pygame.mixer.Sound(sound_file)
                    else:
                        sound = None
                    sounds.append(sound)

# Drawing Helpers
def display_visual_name(name):
    text_surface = font.render(name, True, TEXT_COLOR)
    screen.blit(text_surface, (20, 20))

def display_mode_text(mode_name):
    text_surface = font.render(mode_name, True, TEXT_COLOR)
    x = SCREEN_WIDTH - text_surface.get_width() - 20
    screen.blit(text_surface, (x, 20))

def draw_keypoints_and_bbox(user_data, screen):
    screen.fill(BACKGROUND_COLOR)
    if user_data.frame is not None:
        frame = cv2.resize(user_data.frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
        frame = cv2.flip(frame, 1)
        frame = np.rot90(frame)
        surf = pygame.surfarray.make_surface(frame)
        screen.blit(surf, (0, 0))

        for detection in user_data.detections:
            if detection.get_label() == "person" and detection.get_confidence() >= confidence_threshold:
                bbox = detection.get_bbox()
                x1, y1, x2, y2 = (
                    int(bbox.xmin() * SCREEN_WIDTH),
                    int(bbox.ymin() * SCREEN_HEIGHT),
                    int(bbox.xmax() * SCREEN_WIDTH),
                    int(bbox.ymax() * SCREEN_HEIGHT),
                )
                pygame.draw.rect(screen, BBOX_COLOR, (x1, y1, x2 - x1, y2 - y1), 2)

                if show_keypoints:
                    landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                    if landmarks:
                        points = landmarks[0].get_points()
                        for point in points:
                            x, y = int(point.x() * SCREEN_WIDTH), int(point.y() * SCREEN_HEIGHT)
                            pygame.draw.circle(screen, KEYPOINT_COLOR, (x, y), 3)

def draw_split_screen(user_data, screen):
    screen.fill(BACKGROUND_COLOR)
    if visuals:
        left_surface = screen.subsurface((0, 0, HALF_SCREEN_WIDTH, SCREEN_HEIGHT))
        visuals[current_visual_index].visualize(user_data, left_surface)

    if user_data.frame is not None:
        frame = cv2.resize(user_data.frame, (HALF_SCREEN_WIDTH, SCREEN_HEIGHT))
        frame = cv2.flip(frame, 1)
        frame = np.rot90(frame)
        surf = pygame.surfarray.make_surface(frame)
        screen.blit(surf, (HALF_SCREEN_WIDTH, 0))

        for detection in user_data.detections:
            if detection.get_label() == "person" and detection.get_confidence() >= confidence_threshold:
                bbox = detection.get_bbox()
                x1, y1, x2, y2 = (
                    HALF_SCREEN_WIDTH + int(bbox.xmin() * HALF_SCREEN_WIDTH),
                    int(bbox.ymin() * SCREEN_HEIGHT),
                    HALF_SCREEN_WIDTH + int(bbox.xmax() * HALF_SCREEN_WIDTH),
                    int(bbox.ymax() * SCREEN_HEIGHT),
                )
                pygame.draw.rect(screen, BBOX_COLOR, (x1, y1, x2 - x1, y2 - y1), 2)

# GStreamer Callback with Logging
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    user_data.increment()
    format, width, height = get_caps_from_pad(pad)

    frame = None
    if format and width and height:
        frame = get_numpy_from_buffer(buffer, format, width, height)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    
    # Log tracking ID availability
    for detection in detections:
        track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if track:
            print(f"Tracking ID found: {track[0].get_id()}")
        else:
            print("No tracking ID for detection")
    
    user_data.set_detections(detections)
    return Gst.PadProbeReturn.OK

# Main Visualization Loopimport pygame
import hailo
import random
import math

class HipCirclesVisual:
    def __init__(self):
        self.colors = {}  # {tracking_id: color}

    def visualize(self, user_data, surface):
        surface.fill((0, 0, 0))  # Clear the surface
        detections = user_data.detections
        if not detections:
            return

        for detection in detections:
            if detection.get_label() == "person" and detection.get_confidence() >= 0.5:
                tracking_id = detection.get_tracking_id()
                if tracking_id not in self.colors:
                    self.colors[tracking_id] = (
                        random.randint(100, 255),
                        random.randint(100, 255),
                        random.randint(100, 255)
                    )

                landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                if landmarks:
                    points = landmarks[0].get_points()
                    left_hip = points[11]  # Left hip
                    right_hip = points[12]  # Right hip
                    width, height = surface.get_width(), surface.get_height()
                    hip_x = int((left_hip.x() + right_hip.x()) / 2 * width)
                    hip_y = int((left_hip.y() + right_hip.y()) / 2 * height)

                    radius = 20 + int(10 * math.sin(pygame.time.get_ticks() * 0.01))
                    pygame.draw.circle(surface, self.colors[tracking_id], (hip_x, hip_y), radius, 3)

VisualClass = HipCirclesVisual
def run_visualization(user_data):
    global screen_state, current_visual_index, show_keypoints, current_sound
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_q):
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    screen_state = (screen_state + 1) % 3
                elif event.key == pygame.K_LEFT:
                    screen_state = (screen_state - 1) % 3
                elif (screen_state in [0, 1]) and event.key == pygame.K_UP:
                    if visuals:
                        current_visual_index = (current_visual_index + 1) % len(visuals)
                elif (screen_state in [0, 1]) and event.key == pygame.K_DOWN:
                    if visuals:
                        current_visual_index = (current_visual_index - 1) % len(visuals)
                elif event.key == pygame.K_k:
                    show_keypoints = not show_keypoints

        # Manage audio playback
        if screen_state in [0, 1]:
            new_sound = sounds[current_visual_index] if current_visual_index < len(sounds) else None
            if new_sound != current_sound:
                if current_sound:
                    current_sound.stop()
                current_sound = new_sound
                if current_sound:
                    current_sound.play(loops=-1)
        else:
            if current_sound:
                current_sound.stop()
                current_sound = None

        # Visualization
        try:
            if screen_state == 0:
                if visuals:
                    visuals[current_visual_index].visualize(user_data, screen)
                    display_visual_name(visual_names[current_visual_index])
                display_mode_text("Visual Only")
            elif screen_state == 1:
                draw_split_screen(user_data, screen)
                display_visual_name(visual_names[current_visual_index])
                display_mode_text("Split-Screen Mode")
            elif screen_state == 2:
                draw_keypoints_and_bbox(user_data, screen)
                display_mode_text(f"Keypoints & BBox (KPs: {'On' if show_keypoints else 'Off'})")

            pygame.display.flip()
            clock.tick(30)
        except Exception as e:
            print(f"Error in visualization: {e}")

    if current_sound:
        current_sound.stop()
    pygame.quit()
    os._exit(0)

# Define the subclass for user_data
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.detections = []

    def set_frame(self, frame):
        self.frame = frame

    def set_detections(self, detections):
        self.detections = detections

# Main Execution
if __name__ == "__main__":
    load_visuals()

    user_data = user_app_callback_class()  # Use the subclass
    app = GStreamerPoseEstimationApp(app_callback, user_data)
    gst_thread = threading.Thread(target=app.run, daemon=True)
    gst_thread.start()
    run_visualization(user_data)
