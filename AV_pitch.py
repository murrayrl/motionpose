## Code from AV_2.py #####

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
pygame.mixer.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_width(), screen.get_height()
HALF_SCREEN_WIDTH = SCREEN_WIDTH // 2
pygame.display.set_caption("Enhanced Pose Estimation with Audio")

clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)
is_fullscreen = True

# Colors
BACKGROUND_COLOR = (0, 0, 0)
TEXT_COLOR = (255, 255, 0)
LEFT_TRAIL_COLOR = (0, 255, 0)
RIGHT_TRAIL_COLOR = (0, 0, 255)
BBOX_COLOR = (255, 255, 0)
KEYPOINT_COLOR = (255, 0, 0)

# Visualization settings
visuals = []
visual_names = []
sounds = []
current_visual_index = 0
screen_state = 1  # Start in split-screen mode
confidence_threshold = 0.5
show_keypoints = True
current_sound = None
tutorial_sound_enabled = True
sound_array = []

# Motion trail storage
trail_length = 30
left_wrist_trail = []
right_wrist_trail = []

# Load visuals and sounds
def load_visuals():
    visuals_dir = "multi_person_visuals"
    sounds_dir = "sounds"
    if os.path.exists(visuals_dir):
        for file in os.listdir(visuals_dir):
            if file.endswith(".py"):
                module_name = file[:-3]  # Remove .py
                module_path = os.path.join(visuals_dir, file)
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "VisualClass"):
                    visual_instance = module.VisualClass()
                    visuals.append(visual_instance)
                    base_name = module_name.replace("Visual", "").replace("_", " ").strip()
                    visual_names.append(base_name.title())
                    sound_file = os.path.join(sounds_dir, module_name + ".wav")
                    if os.path.exists(sound_file):
                        # Select pitch factor > 1 for higher pitch, < 1 for lower pitch
                        pitch_factor = 1.5

                        sound = pygame.mixer.Sound(sound_file)
                        sound_array = pygame.sndarray.array(sound)
                        print("Sound Array Shape: ", sound_array.shape)
                        sound_array = sound_array.flatten()
                        print("New Sound Array Shape: ", sound_array.shape)
                        sound_array = change_pitch(sound_array, pitch_factor)
                        sound = pygame.sndarray.make_sound(sound_array)
                       # sound = AudioSegment.from_file(sound_file)
                       # sound = change_pitch_pydub(sound, pitch_factor)
                       # sound = pygame.mixer.Sound(sound_file)
                    else:
                        sound = None
                    sounds.append(sound)

# Change Pitch option 1
def change_pitch(sound_array, pitch_factor):
    len_new = int(len(sound_array) / pitch_factor)
    print(len_new)
    print(len(sound_array))
    new_sound_array = np.interp(
            np.linspace(0, len(sound_array), len_new),
            np.arange(len(sound_array)),
            sound_array
            ).astype(sound_array.dtype)
    new_sound_array = new_sound_array.reshape(int(len_new / 2), 2)
    return new_sound_array

# Change Pitch option 2 (probably not possible because pydub vs pygame but it's whatever)
def change_pitch_pydub(sound, pitch_factor):
    new_sound = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * pitch_factor)
        }).set_frame_rate(sound.frame_rate)
    return new_sound

# Drawing Helpers
def draw_motion_trails(user_data, screen):
    screen.fill(BACKGROUND_COLOR)
    draw_trail(screen, left_wrist_trail, LEFT_TRAIL_COLOR)
    draw_trail(screen, right_wrist_trail, RIGHT_TRAIL_COLOR)

def draw_trail(screen, trail, color):
    if len(trail) < 2:
        return
    width, height = screen.get_width(), screen.get_height()
    for i in range(len(trail) - 1):
        x1, y1 = int(trail[i][0] * width), int(trail[i][1] * height)
        x2, y2 = int(trail[i + 1][0] * width), int(trail[i + 1][1] * height)
        pygame.draw.line(screen, color, (x1, y1), (x2, y2), 5)

def display_visual_name(name, is_default=False):
    if is_default:
        name += " - Single Person"
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

def is_person_detected(user_data):
    for detection in user_data.detections:
        if detection.get_label() == "person" and detection.get_confidence() >= confidence_threshold:
            return True
    return False

# GStreamer Callback
def app_callback(pad, info, user_data):
    global left_wrist_trail, right_wrist_trail
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

    for detection in detections:
        if detection.get_label() == "person" and detection.get_confidence() >= confidence_threshold:
            landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
            if landmarks:
                points = landmarks[0].get_points()
                left_wrist = points[9]
                right_wrist = points[10]
                update_trail(left_wrist_trail, (left_wrist.x(), left_wrist.y()))
                update_trail(right_wrist_trail, (right_wrist.x(), right_wrist.y()))
            break

    user_data.set_detections(detections)
    return Gst.PadProbeReturn.OK

def update_trail(trail, new_point):
    trail.append(new_point)
    if len(trail) > trail_length:
        trail.pop(0)

class MotionTrailsVisual:
    def visualize(self, user_data, surface):
        draw_motion_trails(user_data, surface)

# Main Visualization Loop
def run_visualization(user_data):
    global screen_state, current_visual_index, show_keypoints, current_sound, is_fullscreen, screen, SCREEN_WIDTH, SCREEN_HEIGHT, HALF_SCREEN_WIDTH, tutorial_sound_enabled
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
                elif event.key == pygame.K_p:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_width(), screen.get_height()
                    else:
                        screen = pygame.display.set_mode((1280, 720), 0)
                        SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
                    HALF_SCREEN_WIDTH = SCREEN_WIDTH // 2
                elif event.key == pygame.K_t:
                    if current_visual_index != 0 or screen_state != 1:
                        screen_state = 1
                        current_visual_index = 0
                        tutorial_sound_enabled = True
                    else:
                        tutorial_sound_enabled = not tutorial_sound_enabled

        # Manage audio playback
        if screen_state in [0, 1] and is_person_detected(user_data):
            if current_visual_index == 0 and not tutorial_sound_enabled:
                new_sound = None
            else:
                new_sound = sounds[current_visual_index] if current_visual_index < len(sounds) else None
        else:
            new_sound = None

        if new_sound != current_sound:
            if current_sound:
                current_sound.stop()
            current_sound = new_sound
            if current_sound:
                current_sound.play(loops=-1)

        # Visualization
        try:
            if screen_state == 0:
                if visuals:
                    visuals[current_visual_index].visualize(user_data, screen)
                    display_visual_name(visual_names[current_visual_index], is_default=(current_visual_index == 0))
                display_mode_text("Visual Only")
            elif screen_state == 1:
                draw_split_screen(user_data, screen)
                display_visual_name(visual_names[current_visual_index], is_default=(current_visual_index == 0))
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

class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.detections = []

    def set_frame(self, frame):
        self.frame = frame

    def set_detections(self, detections):
        self.detections = detections

if __name__ == "__main__":
    visuals.insert(0, MotionTrailsVisual())
    visual_names.insert(0, "Motion Trails")
    welcome_sound_path = "welcome.wav"
    if os.path.exists(welcome_sound_path):
        welcome_sound = pygame.mixer.Sound(welcome_sound_path)
        welcome_sound.play()
        print("Playing welcome.wav")
        sounds.insert(0, welcome_sound)
    else:
        print("welcome.wav not found in current directory")
        sounds.insert(0, None)

    load_visuals()
    user_data = user_app_callback_class()
    app = GStreamerPoseEstimationApp(app_callback, user_data)
    gst_thread = threading.Thread(target=app.run, daemon=True)
    gst_thread.start()
    run_visualization(user_data)

    ### End of AV_2.py ###
