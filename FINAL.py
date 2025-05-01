import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
import os
import math
import threading
import importlib.util
import cv2
import numpy as np
import pygame
import hailo

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad, get_numpy_from_buffer, app_callback_class,
)
from hailo_apps_infra.pose_estimation_pipeline import GStreamerPoseEstimationApp

# Initialization
Gst.init(None)
pygame.init()
pygame.mixer.quit()  # GStreamer owns audio

is_fullscreen = True
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_width(), screen.get_height()
HALF_SCREEN_WIDTH = SCREEN_WIDTH // 2
pygame.display.set_caption("Pose-Audio Demo")

clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)

# Colors
BG_COLOR = (0, 0, 0)
TXT_COLOR = (255, 255, 0)
LEFT_TRAIL_CLR = (0, 255, 0)
RIGHT_TRAIL_CLR = (0, 0, 255)
BBOX_COLOR = (255, 255, 0)  # Yellow for bounding boxes

# State Variables
visuals, visual_names = [], []
current_visual_index = 0
screen_state = 1  # 0: visual only | 1: split-screen | 2: frame+keypoints
confidence_thr = 0.5
tutorial_sound_on = True
trail_len = 30
audio_pipelines = {}  # {pid: (pipeline, pitch, eq, vol, pan, sound_file)}
current_sound = None
welcome_played = False
welcome_pipeline = None

# Audio Functions
def get_sound_path(idx: int) -> str | None:
    """Retrieve the sound file path from the normalized_sounds directory."""
    stem = visual_names[idx].replace(' ', '') + "Visual.wav"
    path = os.path.join(os.getcwd(), "normalized_sounds", stem)
    if not os.path.exists(path):
        print(f"Sound file not found for {visual_names[idx]}: {path}")
    else:
        print(f"Found sound file for {visual_names[idx]}: {path}")
    return path if os.path.exists(path) else None

def make_audio_pipeline(sound_file: str, pid: str, xpos: float, idx: int):
    """Create and return a GStreamer audio pipeline for a person."""
    pl = Gst.Pipeline.new(pid)
    def make(name): return Gst.ElementFactory.make(name, None)
    filesrc, decodebin = make("filesrc"), make("decodebin")
    aconv, aresamp = make("audioconvert"), make("audioresample")
    pitch, pan = make("pitch"), make("audiopanorama")
    eq, vol, sink = make("equalizer-10bands"), make("volume"), make("autoaudiosink")
    for e in (filesrc, decodebin, aconv, aresamp, pitch, pan, eq, vol, sink):
        pl.add(e)
    filesrc.set_property("location", sound_file)
    filesrc.link(decodebin)
    decodebin.connect("pad-added", lambda element, pad: pad.link(aconv.get_static_pad("sink")))
    aconv.link(aresamp)
    aresamp.link(pitch)
    pitch.link(pan)
    pan.link(eq)
    eq.link(vol)
    vol.link(sink)
    vis_name = visual_names[current_visual_index]
    if vis_name == "FeetHeatmap":
        eq.set_property("band0", 6.0 * idx)
        eq.set_property("band1", 6.0 * idx)
    elif vis_name == "HipCircles":
        vol.set_property("volume", min(1.0, 0.5 + 0.2 * idx))
    elif vis_name == "Skeleton":
        pitch.set_property("pitch", 1.0 + 0.05 * idx)
    pan.set_property("panorama", 2 * xpos - 1)
    bus = pl.get_bus()
    bus.add_signal_watch()
    def on_message(bus, msg):
        if msg.type == Gst.MessageType.EOS:
            pl.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0)
        elif msg.type == Gst.MessageType.ERROR:
            print(f"Audio pipeline error for {pid}: {msg.parse_error()}")
            pl.set_state(Gst.State.NULL)
    bus.connect("message", on_message)
    pl.set_state(Gst.State.PLAYING)
    return pl, pitch, eq, vol, pan, sound_file

def play_sound_once(sound_file):
    """Play a sound file once (e.g., welcome.wav)."""
    global welcome_pipeline
    pl = Gst.Pipeline.new("welcome_pipeline")
    filesrc = Gst.ElementFactory.make("filesrc", "filesrc")
    decodebin = Gst.ElementFactory.make("decodebin", "decodebin")
    aconv = Gst.ElementFactory.make("audioconvert", "audioconvert")
    sink = Gst.ElementFactory.make("autoaudiosink", "sink")
    for e in (filesrc, decodebin, aconv, sink):
        pl.add(e)
    filesrc.set_property("location", sound_file)
    filesrc.link(decodebin)
    decodebin.connect("pad-added", lambda element, pad: pad.link(aconv.get_static_pad("sink")))
    aconv.link(sink)
    pl.set_state(Gst.State.PLAYING)
    bus = pl.get_bus()
    bus.add_signal_watch()
    def on_message(bus, msg):
        if msg.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR):
            pl.set_state(Gst.State.NULL)
            global welcome_pipeline
            welcome_pipeline = None
    bus.connect("message", on_message)
    welcome_pipeline = pl

# Visualization Loading
def load_visuals():
    """Load visualization modules from multi_person_visuals directory."""
    vdir = "multi_person_visuals"
    if not os.path.isdir(vdir):
        return
    for f in os.listdir(vdir):
        if not f.endswith(".py"):
            continue
        mod_name = f[:-3]
        spec = importlib.util.spec_from_file_location(mod_name, os.path.join(vdir, f))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "VisualClass"):
            visuals.append(module.VisualClass())
            visual_name = mod_name.replace("Visual", "")
            visual_names.append(visual_name)

# Drawing Helpers
def draw_line_trails(surface, trails_to_draw):
    """Draw motion trails on the surface."""
    surface.fill(BG_COLOR)
    w, h = surface.get_width(), surface.get_height()
    for pid, trails in trails_to_draw.items():
        for key, color in (("left_wrist", LEFT_TRAIL_CLR), ("right_wrist", RIGHT_TRAIL_CLR)):
            t = trails.get(key, [])
            if len(t) < 2:
                continue
            pts = [(int(x * w), int(y * h)) for x, y in t]
            pygame.draw.lines(surface, color, False, pts, 5)

def draw_split_screen(user_data, trails_to_draw=None):
    """Draw a split-screen view with visualization and video frame including bounding boxes."""
    screen.fill(BG_COLOR)
    left = screen.subsurface((0, 0, HALF_SCREEN_WIDTH, SCREEN_HEIGHT))
    left.fill(BG_COLOR)
    if current_visual_index == 0:
        draw_line_trails(left, trails_to_draw if trails_to_draw else {})
    else:
        visuals[current_visual_index].visualize(user_data, left)
    if user_data.frame is not None:
        frm = cv2.flip(cv2.resize(user_data.frame, (HALF_SCREEN_WIDTH, SCREEN_HEIGHT)), 1)
        surf = pygame.surfarray.make_surface(np.rot90(frm))
        screen.blit(surf, (HALF_SCREEN_WIDTH, 0))
        for det in user_data.detections:
            if det.get_label() == "person" and det.get_confidence() >= confidence_thr:
                bbox = det.get_bbox()
                x1 = HALF_SCREEN_WIDTH + int(bbox.xmin() * HALF_SCREEN_WIDTH)
                y1 = int(bbox.ymin() * SCREEN_HEIGHT)
                x2 = HALF_SCREEN_WIDTH + int(bbox.xmax() * HALF_SCREEN_WIDTH)
                y2 = int(bbox.ymax() * SCREEN_HEIGHT)
                pygame.draw.rect(screen, BBOX_COLOR, (x1, y1, x2 - x1, y2 - y1), 2)

def overlay_text(txt, x=20, y=20):
    """Overlay text on the screen."""
    surf = font.render(txt, True, TXT_COLOR)
    screen.blit(surf, (x, y))

# GStreamer Callback
def app_callback(pad, info, user_data):
    """Process video buffer and update user data."""
    buf = info.get_buffer()
    user_data.increment()
    fmt, w, h = get_caps_from_pad(pad)
    if fmt and w and h:
        frm = get_numpy_from_buffer(buf, fmt, w, h)
        user_data.set_frame(cv2.cvtColor(frm, cv2.COLOR_RGB2BGR))
    roi = hailo.get_roi_from_buffer(buf)
    dets = roi.get_objects_typed(hailo.HAILO_DETECTION)
    user_data.person_trails.clear()
    for i, det in enumerate(dets):
        if det.get_label() != "person" or det.get_confidence() < confidence_thr:
            continue
        pid = f"person_{i}"
        user_data.person_trails.setdefault(pid, {})
        lms = det.get_objects_typed(hailo.HAILO_LANDMARKS)
        pts = lms[0].get_points() if lms else None
        if not pts:
            continue
        for kp_idx, kp_key in ((9, "left_wrist"), (10, "right_wrist")):
            if kp_idx < len(pts):
                trail = user_data.person_trails[pid].setdefault(kp_key, [])
                trail.append((pts[kp_idx].x(), pts[kp_idx].y()))
                if len(trail) > trail_len:
                    trail.pop(0)
    user_data.set_detections(dets)
    return Gst.PadProbeReturn.OK

# Audio Management
def update_audio_per_person(detections, sound_to_play, people_to_play):
    """Update audio pipelines based on detected people and current sound."""
    global audio_pipelines, current_sound
    if sound_to_play != current_sound:
        for pl, *_ in audio_pipelines.values():
            pl.set_state(Gst.State.NULL)
        audio_pipelines.clear()
        current_sound = sound_to_play
    for pid in list(audio_pipelines):
        if pid not in people_to_play:
            audio_pipelines[pid][0].set_state(Gst.State.NULL)
            del audio_pipelines[pid]
    for pid in people_to_play:
        if pid not in audio_pipelines:
            start_position = 0
            if current_visual_index != 0 and sound_to_play:
                existing_entry = next(((pl, s) for pl, _, _, _, _, s in audio_pipelines.values() if s == sound_to_play), None)
                if existing_entry:
                    existing_pl, _ = existing_entry
                    success, position = existing_pl.query_position(Gst.Format.TIME)
                    if success:
                        start_position = position
            for i, det in enumerate(detections):
                if f"person_{i}" == pid:
                    bbox = det.get_bbox()
                    cx = (bbox.xmin() + bbox.xmax()) / 2
                    break
            else:
                cx = 0.5
            pl, pitch, eq, vol, pan, sound_file = make_audio_pipeline(sound_to_play, pid, cx, 0)
            pl.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, start_position)
            audio_pipelines[pid] = (pl, pitch, eq, vol, pan, sound_file)
        else:
            pan = audio_pipelines[pid][4]
            for i, det in enumerate(detections):
                if f"person_{i}" == pid:
                    bbox = det.get_bbox()
                    cx = (bbox.xmin() + bbox.xmax()) / 2
                    break
            else:
                cx = 0.5
            pan.set_property("panorama", 2 * cx - 1)

# Main Visualization Loop
def run_visualisation(user_data):
    """Run the main visualization loop."""
    global current_visual_index, screen_state, tutorial_sound_on, is_fullscreen, screen, SCREEN_WIDTH, SCREEN_HEIGHT, HALF_SCREEN_WIDTH, welcome_played, welcome_pipeline
    show_keypoints = True
    prev_person_count = 0
    running = True
    while running:
        pygame.event.pump()
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_q):
                running = False
            elif e.type == pygame.KEYDOWN:
                match e.key:
                    case pygame.K_RIGHT: screen_state = (screen_state + 1) % 3
                    case pygame.K_LEFT: screen_state = (screen_state - 1) % 3
                    case pygame.K_UP if visuals: current_visual_index = (current_visual_index + 1) % len(visuals)
                    case pygame.K_DOWN if visuals: current_visual_index = (current_visual_index - 1) % len(visuals)
                    case pygame.K_k: show_keypoints = not show_keypoints
                    case pygame.K_p:
                        is_fullscreen = not is_fullscreen
                        if is_fullscreen:
                            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                            SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_width(), screen.get_height()
                        else:
                            screen = pygame.display.set_mode((1280, 720))
                            SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
                        HALF_SCREEN_WIDTH = SCREEN_WIDTH // 2
                    case pygame.K_t:
                        print("T key pressed")
                        if current_visual_index == 0:
                            tutorial_sound_on = not tutorial_sound_on
                            if not tutorial_sound_on and welcome_pipeline:
                                welcome_pipeline.set_state(Gst.State.NULL)
                                welcome_pipeline = None
                                print("Stopped welcome sound pipeline")
                            welcome_played = False
                            print(f"Tutorial sound toggled to {tutorial_sound_on}")
                        else:
                            current_visual_index = 0
                            tutorial_sound_on = True
                            welcome_played = False
                            if welcome_pipeline:
                                welcome_pipeline.set_state(Gst.State.NULL)
                                welcome_pipeline = None
                            print("Switched to Motion Trails with tutorial sound on")

        # Determine audio to play
        if screen_state in (0, 1):
            current_person_count = len(user_data.person_trails)
            if current_visual_index == 0 and tutorial_sound_on and current_person_count > 0 and not welcome_played and not welcome_pipeline:
                welcome_sound_path = os.path.join(os.getcwd(), "welcome.wav")
                if os.path.exists(welcome_sound_path):
                    print("Playing welcome sound")
                    play_sound_once(welcome_sound_path)
                    welcome_played = True
                sound_to_play = None
                people_to_play = []
            elif current_person_count == 0 and welcome_pipeline:
                welcome_pipeline.set_state(Gst.State.NULL)
                welcome_pipeline = None
                sound_to_play = None
                people_to_play = []
            else:
                sound_to_play = get_sound_path(current_visual_index)
                if sound_to_play and user_data.person_trails:
                    people_to_play = list(user_data.person_trails.keys())
                else:
                    people_to_play = []
            prev_person_count = current_person_count
        else:
            if welcome_pipeline:
                welcome_pipeline.set_state(Gst.State.NULL)
                welcome_pipeline = None
            sound_to_play = None
            people_to_play = []

        update_audio_per_person(user_data.detections, sound_to_play, people_to_play)
        print(f"Current visual: {visual_names[current_visual_index]}, People detected: {len(user_data.person_trails)}, Sound: {sound_to_play}, Welcome played: {welcome_played}")

        # Render screen
        if screen_state == 0:
            screen.fill(BG_COLOR)
            if current_visual_index == 0:
                trails_to_draw = {}
                draw_line_trails(screen, trails_to_draw)
            else:
                visuals[current_visual_index].visualize(user_data, screen)
            overlay_text(visual_names[current_visual_index], 20, 20)
            overlay_text("Visual Only", SCREEN_WIDTH - 180, 20)
        elif screen_state == 1:
            draw_split_screen(user_data, {})
            overlay_text(visual_names[current_visual_index], 20, 20)
            overlay_text("Split-Screen", SCREEN_WIDTH - 200, 20)
        else:
            screen.fill(BG_COLOR)
            if user_data.frame is not None:
                frm = cv2.flip(cv2.resize(user_data.frame, (SCREEN_WIDTH, SCREEN_HEIGHT)), 1)
                screen.blit(pygame.surfarray.make_surface(np.rot90(frm)), (0, 0))
                for det in user_data.detections:
                    if det.get_label() == "person" and det.get_confidence() >= confidence_thr:
                        bbox = det.get_bbox()
                        x1, y1, x2, y2 = (
                            int(bbox.xmin() * SCREEN_WIDTH),
                            int(bbox.ymin() * SCREEN_HEIGHT),
                            int(bbox.xmax() * SCREEN_WIDTH),
                            int(bbox.ymax() * SCREEN_HEIGHT),
                        )
                        pygame.draw.rect(screen, BBOX_COLOR, (x1, y1, x2 - x1, y2 - y1), 2)
                        if show_keypoints:
                            lms = det.get_objects_typed(hailo.HAILO_LANDMARKS)
                            if lms:
                                pts = lms[0].get_points()
                                for pt in pts:
                                    x, y = int(pt.x() * SCREEN_WIDTH), int(pt.y() * SCREEN_HEIGHT)
                                    pygame.draw.circle(screen, (255, 0, 0), (x, y), 3)
            overlay_text(f"Keypoints Mode ({'On' if show_keypoints else 'Off'})", SCREEN_WIDTH - 320, 20)

        pygame.display.flip()
        clock.tick(30)

    # Cleanup
    if welcome_pipeline:
        welcome_pipeline.set_state(Gst.State.NULL)
    for pl, *_ in audio_pipelines.values():
        pl.set_state(Gst.State.NULL)
    pygame.quit()
    os._exit(0)

# User Data Class
class UserData(app_callback_class):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.detections = []
        self.person_trails = {}

    def set_frame(self, f):
        self.frame = f

    def set_detections(self, d):
        self.detections = d

# Main Execution
if __name__ == "__main__":
    class MotionTrailsVisual:
        def visualize(self, user_data, surface):
            draw_line_trails(surface, user_data.person_trails)
    visuals.insert(0, MotionTrailsVisual())
    visual_names.insert(0, "Motion Trails")
    load_visuals()
    print("Loaded visualizations:", visual_names)
    user_data = UserData()
    app = GStreamerPoseEstimationApp(app_callback, user_data)
    threading.Thread(target=app.run, daemon=True).start()
    run_visualisation(user_data)
