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
pygame.mixer.quit()  # Disable Pygame's mixer to avoid conflicts with GStreamer
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
current_visual_index = 0
screen_state = 1  # Start in split-screen mode
confidence_threshold = 0.5
show_keypoints = True
tutorial_sound_enabled = True

# Motion trail storage
trail_length = 30
person_trails = {}  # Dictionary to store trails per person

# GStreamer audio pipelines for multiple sounds per person and keypoint
audio_pipelines = {}

def create_audio_pipeline(sound_file):
    pipeline = Gst.Pipeline()
    source = Gst.ElementFactory.make("filesrc", "source")
    decodebin = Gst.ElementFactory.make("decodebin", "decodebin")
    audioconvert = Gst.ElementFactory.make("audioconvert", "audioconvert")
    audioresample = Gst.ElementFactory.make("audioresample", "audioresample")
    pitch = Gst.ElementFactory.make("pitch", "pitch")
    equalizer = Gst.ElementFactory.make("equalizer-10bands", "equalizer")
    volume = Gst.ElementFactory.make("volume", "volume")
    sink = Gst.ElementFactory.make("autoaudiosink", "sink")

    pipeline.add(source)
    pipeline.add(decodebin)
    pipeline.add(audioconvert)
    pipeline.add(audioresample)
    pipeline.add(pitch)
    pipeline.add(equalizer)
    pipeline.add(volume)
    pipeline.add(sink)

    source.link(decodebin)
    decodebin.connect("pad-added", lambda dbin, pad: pad.link(audioconvert.get_static_pad("sink")))
    audioconvert.link(audioresample)
    audioresample.link(pitch)
    pitch.link(equalizer)
    equalizer.link(volume)
    volume.link(sink)

    source.set_property("location", sound_file)
    return pipeline, pitch, equalizer, volume

# Load visuals
def load_visuals():
    visuals_dir = "multi_person_visuals"
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
                    base_name = module_name.replace("Visual", "").replace("_", " ").strip()
                    visual_names.append(base_name.title())

# Drawing Helpers
def draw_motion_trails(user_data, screen):
    screen.fill(BACKGROUND_COLOR)
    for person_id, trails in person_trails.items():
        draw_trail(screen, trails.get('left_wrist', []), LEFT_TRAIL_COLOR)
        draw_trail(screen, trails.get('right_wrist', []), RIGHT_TRAIL_COLOR)

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

def get_person_count(user_data):
    return sum(1 for detection in user_data.detections if detection.get_label() == "person" and detection.get_confidence() >= confidence_threshold)

# GStreamer Callback
def app_callback(pad, info, user_data):
    global person_trails
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
    person_trails.clear()  # Reset trails each frame

    for idx, detection in enumerate(detections):
        if detection.get_label() == "person" and detection.get_confidence() >= confidence_threshold:
            person_id = f"person_{idx}"
            person_trails[person_id] = person_trails.get(person_id, {})
            landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
            if landmarks:
                points = landmarks[0].get_points()
                # Keypoint indices: 9 = left wrist, 10 = right wrist, 7 = left elbow, 8 = right elbow
                keypoints = {
                    'left_wrist': points[9] if len(points) > 9 else None,
                    'right_wrist': points[10] if len(points) > 10 else None,
                    'left_elbow': points[7] if len(points) > 7 else None,
                    'right_elbow': points[8] if len(points) > 8 else None,
                }
                for key, point in keypoints.items():
                    if point:
                        trail = person_trails[person_id].get(key, [])
                        update_trail(trail, (point.x(), point.y()))
                        person_trails[person_id][key] = trail

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
    global screen_state, current_visual_index, show_keypoints, is_fullscreen, screen, SCREEN_WIDTH, SCREEN_HEIGHT, HALF_SCREEN_WIDTH, tutorial_sound_enabled
    running = True
    current_sound_file = None
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
        person_count = get_person_count(user_data)
        if screen_state in [0, 1] and person_count > 0:
            if current_visual_index == 0 and not tutorial_sound_enabled:
                new_sound_file = None
            else:
                sound_file = f"sounds/{visual_names[current_visual_index].replace(' ', '_').lower()}.wav"
                if os.path.exists(sound_file):
                    new_sound_file = sound_file
                else:
                    new_sound_file = None
        else:
            new_sound_file = None

        if new_sound_file != current_sound_file:
            if new_sound_file:
                audio_pipelines.clear()
                for person_id in person_trails.keys():
                    for keypoint in ['left_elbow', 'right_elbow', 'left_wrist']:
                        pipeline_key = f"{person_id}_{keypoint}_{new_sound_file}"
                        pipeline, pitch, equalizer, volume = create_audio_pipeline(new_sound_file)
                        audio_pipelines[pipeline_key] = (pipeline, pitch, equalizer, volume)
                        pipeline.set_state(Gst.State.PLAYING)
            else:
                for pipeline in audio_pipelines.values():
                    pipeline[0].set_state(Gst.State.NULL)
                audio_pipelines.clear()
            current_sound_file = new_sound_file

        # Apply audio effects based on person count and movement
        if person_count > 0 and current_sound_file:
            for person_id, trails in person_trails.items():
                # AccelerationGlowVisual - Single manipulation per person
                if visual_names[current_visual_index] == "Acceleration Glow":
                    pipeline_key = f"{person_id}_left_wrist_{current_sound_file}"
                    if pipeline_key in audio_pipelines:
                        pipeline, pitch, equalizer, volume = audio_pipelines[pipeline_key]
                        trail = trails.get('left_wrist', [])
                        if len(trail) > 1:
                            speed = calculate_speed(trail[-2], trail[-1])
                            pitch.set_property("pitch", max(0.5, min(2.0, 1.0 + speed / 100.0)))
                            volume.set_property("volume", min(1.0, 0.5 + person_count * 0.1))

                # ElbowTrailsVisual - Separate manipulations for each elbow
                elif visual_names[current_visual_index] == "Elbow Trails":
                    for side, keypoint in [('left', 'left_elbow'), ('right', 'right_elbow')]:
                        pipeline_key = f"{person_id}_{keypoint}_{current_sound_file}"
                        if pipeline_key in audio_pipelines:
                            pipeline, pitch, equalizer, volume = audio_pipelines[pipeline_key]
                            trail = trails.get(keypoint, [])
                            if len(trail) > 1:
                                speed = calculate_speed(trail[-2], trail[-1])
                                pitch_shift = 1.0 + speed / 100.0 if side == 'left' else 1.0 + speed / 50.0
                                pitch.set_property("pitch", max(0.5, min(2.0, pitch_shift)))
                                # Panning simulation via volume
                                volume.set_property("volume", min(1.0, 0.5 + speed / 100.0))

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

    for pipeline in audio_pipelines.values():
        pipeline[0].set_state(Gst.State.NULL)
    pygame.quit()
    os._exit(0)

def calculate_speed(prev_pos, current_pos):
    return ((current_pos[0] - prev_pos[0]) ** 2 + (current_pos[1] - prev_pos[1]) ** 2) ** 0.5

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
    load_visuals()
    user_data = user_app_callback_class()
    app = GStreamerPoseEstimationApp(app_callback, user_data)
    gst_thread = threading.Thread(target=app.run, daemon=True)
    gst_thread.start()
    run_visualization(user_data)
