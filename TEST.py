#!/usr/bin/env python3
# INTEGRATED.py – enhanced multi-person audio-visual pose streamer
# ───────────────────────────────────────────────────────────────────
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
import os
import math           # loudness → volume multiplier
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

# ── Init ───────────────────────────────────────────────────────────
Gst.init(None)
pygame.init()
pygame.mixer.quit()        # we’ll let GStreamer own audio

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SCREEN_WIDTH,  SCREEN_HEIGHT  = screen.get_width(), screen.get_height()
HALF_SCREEN_WIDTH            = SCREEN_WIDTH // 2
pygame.display.set_caption("Enhanced Pose Estimation with Audio")

clock          = pygame.time.Clock()
font           = pygame.font.Font(None, 36)
is_fullscreen  = True

# ── Colours ────────────────────────────────────────────────────────
BACKGROUND_COLOR = (0, 0, 0)
TEXT_COLOR       = (255, 255, 0)
LEFT_TRAIL_COLOR = (0, 255, 0)
RIGHT_TRAIL_COLOR= (0, 0, 255)
BBOX_COLOR       = (255, 255, 0)
KEYPOINT_COLOR   = (255, 0, 0)

# ── State ──────────────────────────────────────────────────────────
visuals: list   = []
visual_names: list = []
current_visual_index  = 0
screen_state          = 1       # 0 visual | 1 split | 2 frame+KP
confidence_threshold  = 0.5
show_keypoints        = True
tutorial_sound_enabled= True

trail_length   = 30
person_trails  = {}             # {person_id: {kp_name: [points]}}
audio_pipelines = {}            # {key: (pipeline, pitch, eq, vol, pan)}

# pre-measured integrated loudness (LUFS)
lufs_values = {
    "AccelerationGlowVisual.wav": -24.18,
    "ElbowTrailsVisual.wav":      -26.72,
    "FeetHeatmapVisual.wav":      -43.33,
    "HipCirclesVisual.wav":       -17.93,
    "SkeletonVisual.wav":         -12.23,
    "SpineLineVisual.wav":        -20.67,
}

# ───────────────────────────────────────────────────────────────────
#  Helper: resolve visual index → existing WAV absolute path
def get_sound_path(idx: int) -> str | None:
    stem = visual_names[idx].replace(" ", "") + "Visual.wav"
    path = os.path.join(os.getcwd(), "sounds", stem)
    return path if os.path.exists(path) else None

# ───────────────────────────────────────────────────────────────────
def create_audio_pipeline(sound_file: str,
                          person_position: float | None = None,
                          person_index: int = 0):
    """Return (pipeline, pitch, eq, vol, pan) ready to set PLAYING."""
    pipeline = Gst.Pipeline()
    filesrc      = Gst.ElementFactory.make("filesrc", "filesrc")
    decodebin    = Gst.ElementFactory.make("decodebin", "decodebin")
    audioconvert = Gst.ElementFactory.make("audioconvert", "audioconvert")
    audioresample= Gst.ElementFactory.make("audioresample", "audioresample")
    pitch        = Gst.ElementFactory.make("pitch", "pitch")
    pan          = Gst.ElementFactory.make("audiopanorama", "pan")
    equalizer    = Gst.ElementFactory.make("equalizer-10bands", "eq")
    volume       = Gst.ElementFactory.make("volume", "vol")
    sink         = Gst.ElementFactory.make("autoaudiosink", "sink")

    for elem in (filesrc, decodebin, audioconvert, audioresample,
                 pitch, pan, equalizer, volume, sink):
        pipeline.add(elem)

    filesrc.set_property("location", sound_file)
    filesrc.link(decodebin)

    def _on_pad_added(_element, pad, _data):
        pad.link(audioconvert.get_static_pad("sink"))
    decodebin.connect("pad-added", _on_pad_added, None)

    audioconvert.link(audioresample)
    audioresample.link(pitch)
    pitch.link(pan)
    pan.link(equalizer)
    equalizer.link(volume)
    volume.link(sink)

    # normalise loudness → –23 LUFS
    base = os.path.basename(sound_file)
    lufs = lufs_values.get(base, -23.0)
    target = -23.0
    volume.set_property("volume",
                        10 ** ((target - lufs) / 20) if lufs < target else 1.0)

    # spatial pan (–1 = left, +1 = right)
    if person_position is not None:
        pan.set_property("panorama", 2 * person_position - 1)

    # ─ debug: print GStreamer errors to stdout
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message::error",
                lambda _b, m: print("[Gst-ERROR]", m.parse_error()[1]))

    return pipeline, pitch, equalizer, volume, pan

# ───────────────────────────────────────────────────────────────────
def load_visuals():
    vdir = "multi_person_visuals"
    if not os.path.isdir(vdir):
        return
    for f in os.listdir(vdir):
        if not f.endswith(".py"):
            continue
        mod_name = f[:-3]
        spec = importlib.util.spec_from_file_location(mod_name,
                                                      os.path.join(vdir, f))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "VisualClass"):
            visuals.append(module.VisualClass())
            base_name = mod_name.replace("Visual", "").replace("_", " ").strip()
            visual_names.append(base_name.title())

# ─────────────────────── drawing helpers ──────────────────────────
def draw_trail(surface, trail, color):
    if len(trail) < 2:
        return
    w, h = surface.get_width(), surface.get_height()
    for i in range(len(trail) - 1):
        x1, y1 = int(trail[i][0] * w), int(trail[i][1] * h)
        x2, y2 = int(trail[i+1][0] * w), int(trail[i+1][1] * h)
        pygame.draw.line(surface, color, (x1, y1), (x2, y2), 5)

def draw_motion_trails(surface):
    surface.fill(BACKGROUND_COLOR)
    for trails in person_trails.values():
        draw_trail(surface, trails.get("left_wrist", []),  LEFT_TRAIL_COLOR)
        draw_trail(surface, trails.get("right_wrist", []), RIGHT_TRAIL_COLOR)

def display_visual_name(name, default=False):
    if default: name += " – Single Person"
    txt = font.render(name, True, TEXT_COLOR)
    screen.blit(txt, (20, 20))

def display_mode_text(txt):
    surf = font.render(txt, True, TEXT_COLOR)
    screen.blit(surf, (SCREEN_WIDTH - surf.get_width() - 20, 20))

# ───────────────────── vision helpers ─────────────────────────────
def draw_split_screen(user_data):
    screen.fill(BACKGROUND_COLOR)
    if visuals:
        left = screen.subsurface((0, 0, HALF_SCREEN_WIDTH, SCREEN_HEIGHT))
        visuals[current_visual_index].visualize(user_data, left)

    if user_data.frame is not None:
        frame = cv2.resize(user_data.frame,
                           (HALF_SCREEN_WIDTH, SCREEN_HEIGHT))
        frame = cv2.flip(frame, 1)
        frame = np.rot90(frame)
        surf = pygame.surfarray.make_surface(frame)
        screen.blit(surf, (HALF_SCREEN_WIDTH, 0))

def get_person_count(user_data):
    return sum(1 for det in user_data.detections
               if det.get_label() == "person"
               and det.get_confidence() >= confidence_threshold)

# ───────────────────── GStreamer callback ─────────────────────────
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
    person_trails.clear()

    for idx, det in enumerate(detections):
        if det.get_label() != "person" or det.get_confidence() < confidence_threshold:
            continue
        pid = f"person_{idx}"
        person_trails.setdefault(pid, {})
        lms = det.get_objects_typed(hailo.HAILO_LANDMARKS)
        if not lms:
            continue
        pts = lms[0].get_points()
        kps = {
            "left_wrist":  pts[9]  if len(pts) > 9  else None,
            "right_wrist": pts[10] if len(pts) > 10 else None,
            "left_elbow":  pts[7]  if len(pts) > 7  else None,
            "right_elbow": pts[8]  if len(pts) > 8  else None,
        }
        for key, pt in kps.items():
            if pt:
                trail = person_trails[pid].get(key, [])
                trail.append((pt.x(), pt.y()))
                if len(trail) > trail_length:
                    trail.pop(0)
                person_trails[pid][key] = trail

    user_data.set_detections(detections)
    return Gst.PadProbeReturn.OK

# ───────────────────── main loop ──────────────────────────────────
def run_visualization(user_data):
    global screen_state, current_visual_index, show_keypoints
    global is_fullscreen, screen, SCREEN_WIDTH, SCREEN_HEIGHT
    global HALF_SCREEN_WIDTH, tutorial_sound_enabled

    running          = True
    current_sound    = None   # absolute path currently playing

    while running:
        # ─── UI/input ───────────────────────────────────────────────
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_q):
                running = False
            elif e.type == pygame.KEYDOWN:
                match e.key:
                    case pygame.K_RIGHT: screen_state = (screen_state + 1) % 3
                    case pygame.K_LEFT:  screen_state = (screen_state - 1) % 3
                    case pygame.K_UP if screen_state in (0,1) and visuals:
                        current_visual_index = (current_visual_index + 1) % len(visuals)
                    case pygame.K_DOWN if screen_state in (0,1) and visuals:
                        current_visual_index = (current_visual_index - 1) % len(visuals)
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
                        if current_visual_index != 0 or screen_state != 1:
                            screen_state = 1
                            current_visual_index = 0
                            tutorial_sound_enabled = True
                        else:
                            tutorial_sound_enabled = not tutorial_sound_enabled

        # ─── Decide what audio (if any) should play ────────────────
        person_count = get_person_count(user_data)
        if screen_state in (0,1) and person_count > 0:
            if current_visual_index == 0 and not tutorial_sound_enabled:
                new_sound = None
            else:
                new_sound = get_sound_path(current_visual_index)
        else:
            new_sound = None

        # ─── If sound selection changed, rebuild pipelines ─────────
        if new_sound != current_sound:
            # stop & drop existing
            for (pl, *_rest) in audio_pipelines.values():
                pl.set_state(Gst.State.NULL)
            audio_pipelines.clear()
            current_sound = new_sound

            if current_sound:
                # one pipeline per person (or per-keypoint, depending visual)
                for idx, det in enumerate(user_data.detections):
                    if det.get_label() != "person" or det.get_confidence() < confidence_threshold:
                        continue
                    pid   = f"person_{idx}"
                    bbox  = det.get_bbox()
                    cx    = (bbox.xmin() + bbox.xmax()) / 2  # 0–1

                    key   = f"{pid}_{current_sound}"
                    pl, pitch, eq, vol, pan = create_audio_pipeline(current_sound,
                                                                    person_position=cx,
                                                                    person_index=idx)
                    # example visual-specific tweaks
                    if visual_names[current_visual_index] == "Feet Heatmap":
                        eq.set_property("band0", 6.0 * idx)
                        eq.set_property("band1", 6.0 * idx)
                    elif visual_names[current_visual_index] == "Hip Circles":
                        vol.set_property("volume", min(1.0, 0.5 + 0.2 * idx))
                    elif visual_names[current_visual_index] == "Skeleton":
                        pitch.set_property("pitch", 1.0 + 0.05 * idx)

                    audio_pipelines[key] = (pl, pitch, eq, vol, pan)
                    pl.set_state(Gst.State.PLAYING)

        # ─── Realtime audio effects (speed → pitch etc.) ───────────
        def kp_speed(t):
            return math.hypot(t[-1][0] - t[-2][0], t[-1][1] - t[-2][1])

        if current_sound and person_trails:
            for pid, trails in person_trails.items():
                if visual_names[current_visual_index] == "Acceleration Glow":
                    key = f"{pid}_{current_sound}"
                    if key in audio_pipelines and "left_wrist" in trails and len(trails["left_wrist"]) > 1:
                        pl, pitch, eq, vol, pan = audio_pipelines[key]
                        speed = kp_speed(trails["left_wrist"])
                        pitch.set_property("pitch", max(0.5, min(2.0, 1.0 + speed*4)))
                        vol  .set_property("volume", min(1.0, 0.5 + person_count*0.1))

        # ─── Render ────────────────────────────────────────────────
        try:
            if screen_state == 0:
                if visuals:
                    visuals[current_visual_index].visualize(user_data, screen)
                    display_visual_name(visual_names[current_visual_index],
                                        default=(current_visual_index == 0))
                display_mode_text("Visual Only")
            elif screen_state == 1:
                draw_split_screen(user_data)
                display_visual_name(visual_names[current_visual_index],
                                    default=(current_visual_index == 0))
                display_mode_text("Split-Screen")
            else:  # 2
                screen.fill(BACKGROUND_COLOR)
                if user_data.frame is not None:
                    frm = cv2.resize(user_data.frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    frm = cv2.flip(frm, 1)
                    frm = np.rot90(frm)
                    surf = pygame.surfarray.make_surface(frm)
                    screen.blit(surf, (0, 0))
                display_mode_text(f"Keypoints & BBox (KPs: {'On' if show_keypoints else 'Off'})")

            pygame.display.flip()
            clock.tick(30)
        except Exception as exc:
            print("[Visualization-err]", exc)

    # on exit
    for (pl, *_rest) in audio_pipelines.values():
        pl.set_state(Gst.State.NULL)
    pygame.quit()
    os._exit(0)

# ───────────────────── boilerplate -- start everything ────────────
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.detections = []

    def set_frame(self, frame):      self.frame = frame
    def set_detections(self, dets):  self.detections = dets

if __name__ == "__main__":
    # default visual = motion trails
    class MotionTrailsVisual:
        def visualize(self, user_data, surface): draw_motion_trails(surface)
    visuals.insert(0, MotionTrailsVisual())
    visual_names.insert(0, "Motion Trails")

    load_visuals()

    user_data = user_app_callback_class()
    app       = GStreamerPoseEstimationApp(app_callback, user_data)
    threading.Thread(target=app.run, daemon=True).start()
    run_visualization(user_data)

