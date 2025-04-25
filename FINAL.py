import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
import os, math, threading, importlib.util, cv2, numpy as np, pygame, hailo

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad, get_numpy_from_buffer, app_callback_class,
)
from hailo_apps_infra.pose_estimation_pipeline import GStreamerPoseEstimationApp

# Init
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

# Colours
BG_COLOR = (0, 0, 0)
TXT_COLOR = (255, 255, 0)
LEFT_TRAIL_CLR = (0, 255, 0)
RIGHT_TRAIL_CLR = (0, 0, 255)

# State
visuals, visual_names = [], []
current_visual_index = 0
screen_state = 1  # 0 visual | 1 split | 2 frame+KP
confidence_thr = 0.5
show_keypoints = True
tutorial_sound_on = True

trail_len = 30
audio_pipelines = {}  # {pid: (pl, pitch, eq, vol, pan, sound_file)}
current_sound = None

def get_sound_path(idx: int) -> str | None:
    stem = visual_names[idx].replace(' ', '') + "Visual.wav"
    path = os.path.join(os.getcwd(), "normalized_sounds", stem)
    return path if os.path.exists(path) else None

def make_audio_pipeline(sound_file: str, pid: str, xpos: float, idx: int):
    """Create and return a pipeline tuple for one person."""
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

    decodebin.connect("pad-added",
        lambda _e, p, _d: p.link(aconv.get_static_pad("sink")))

    aconv.link(aresamp); aresamp.link(pitch); pitch.link(pan)
    pan.link(eq); eq.link(vol); vol.link(sink)

    # Visual-specific tweaks
    vis_name = visual_names[current_visual_index]
    if vis_name == "Feet Heatmap":
        eq.set_property("band0", 6.0 * idx)
        eq.set_property("band1", 6.0 * idx)
    elif vis_name == "Hip Circles":
        vol.set_property("volume", min(1.0, 0.5 + 0.2 * idx))
    elif vis_name == "Skeleton":
        pitch.set_property("pitch", 1.0 + 0.05 * idx)

    # Panorama: -1 left, +1 right
    pan.set_property("panorama", 2 * xpos - 1)

    # Loop the sound
    bus = pl.get_bus()
    bus.add_signal_watch()
    def on_message(bus, msg):
        if msg.type == Gst.MessageType.EOS:
            pl.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0)
        elif msg.type == Gst.MessageType.ERROR:
            pl.set_state(Gst.State.NULL)
    bus.connect("message", on_message)

    pl.set_state(Gst.State.PLAYING)
    return pl, pitch, eq, vol, pan, sound_file

def play_sound_once(sound_file):
    pl = Gst.Pipeline.new("welcome_pipeline")
    filesrc = Gst.ElementFactory.make("filesrc", "filesrc")
    decodebin = Gst.ElementFactory.make("decodebin", "decodebin")
    aconv = Gst.ElementFactory.make("audioconvert", "audioconvert")
    sink = Gst.ElementFactory.make("autoaudiosink", "sink")
    for e in (filesrc, decodebin, aconv, sink):
        pl.add(e)
    filesrc.set_property("location", sound_file)
    filesrc.link(decodebin)
    decodebin.connect("pad-added", lambda _e, p, _d: p.link(aconv.get_static_pad("sink")))
    aconv.link(sink)
    pl.set_state(Gst.State.PLAYING)
    bus = pl.get_bus()
    bus.add_signal_watch()
    def on_message(bus, msg):
        if msg.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR):
            pl.set_state(Gst.State.NULL)
    bus.connect("message", on_message)

def load_visuals():
    vdir = "multi_person_visuals"
    if not os.path.isdir(vdir): return
    for f in os.listdir(vdir):
        if not f.endswith(".py"): continue
        mod_name = f[:-3]
        spec = importlib.util.spec_from_file_location(mod_name,
                                                      os.path.join(vdir, f))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        if hasattr(module, "VisualClass"):
            visuals.append(module.VisualClass())
            visual_names.append(mod_name.replace("Visual", "").replace("_", " ").title())

# Drawing helpers
def draw_line_trails(surface, trails_to_draw):
    surface.fill(BG_COLOR)
    w, h = surface.get_width(), surface.get_height()
    for pid, trails in trails_to_draw.items():
        for key, color in (("left_wrist", LEFT_TRAIL_CLR), ("right_wrist", RIGHT_TRAIL_CLR)):
            t = trails.get(key, [])
            if len(t) < 2: continue
            pts = [(int(x * w), int(y * h)) for x, y in t]
            pygame.draw.lines(surface, color, False, pts, 5)

def draw_split_screen(user_data, trails_to_draw=None):
    screen.fill(BG_COLOR)
    left = screen.subsurface((0, 0, HALF_SCREEN_WIDTH, SCREEN_HEIGHT))
    if current_visual_index == 0:
        draw_line_trails(left, trails_to_draw if trails_to_draw else {})
    else:
        visuals[current_visual_index].visualize(user_data, left)
    if user_data.frame is not None:
        frm = cv2.flip(cv2.resize(user_data.frame, (HALF_SCREEN_WIDTH, SCREEN_HEIGHT)), 1)
        surf = pygame.surfarray.make_surface(np.rot90(frm))
        screen.blit(surf, (HALF_SCREEN_WIDTH, 0))

def overlay_text(txt, x=20, y=20):
    surf = font.render(txt, True, TXT_COLOR); screen.blit(surf, (x, y))

# Pad-probe callback
def app_callback(pad, info, user_data):
    buf = info.get_buffer(); user_data.increment()
    fmt, w, h = get_caps_from_pad(pad)
    if fmt and w and h:
        frm = get_numpy_from_buffer(buf, fmt, w, h)
        user_data.set_frame(cv2.cvtColor(frm, cv2.COLOR_RGB2BGR))

    roi = hailo.get_roi_from_buffer(buf)
    dets = roi.get_objects_typed(hailo.HAILO_DETECTION); user_data.person_trails.clear()

    for i, det in enumerate(dets):
        if det.get_label() != "person" or det.get_confidence() < confidence_thr: continue
        pid = f"person_{i}"
        user_data.person_trails.setdefault(pid, {})
        lms = det.get_objects_typed(hailo.HAILO_LANDMARKS); pts = None
        if lms: pts = lms[0].get_points()
        if not pts: continue
        for kp_idx, kp_key in ((9, "left_wrist"), (10, "right_wrist")):
            if kp_idx < len(pts):
                trail = user_data.person_trails[pid].setdefault(kp_key, [])
                trail.append((pts[kp_idx].x(), pts[kp_idx].y()))
                if len(trail) > trail_len: trail.pop(0)
    user_data.set_detections(dets)
    return Gst.PadProbeReturn.OK

# Main loop
def update_audio_per_person(detections, sound_to_play, people_to_play):
    global audio_pipelines, current_sound
    if sound_to_play != current_sound:
        for pl, *_ in audio_pipelines.values():
            pl.set_state(Gst.State.NULL)
        audio_pipelines.clear()
        current_sound = sound_to_play

    # Stop pipelines not in people_to_play
    for pid in list(audio_pipelines):
        if pid not in people_to_play:
            audio_pipelines[pid][0].set_state(Gst.State.NULL)
            del audio_pipelines[pid]

    # Create or update pipelines for people_to_play
    for pid in people_to_play:
        if pid not in audio_pipelines:
            start_position = 0
            if current_visual_index != 0 and sound_to_play:
                # Find an existing pipeline for the same sound
                existing_entry = next(((pl, s) for pl, _, _, _, _, s in audio_pipelines.values() if s == sound_to_play), None)
                if existing_entry:
                    existing_pl, _ = existing_entry
                    success, position = existing_pl.query_position(Gst.Format.TIME)
                    if success:
                        start_position = position
            # Create new pipeline
            for i, det in enumerate(detections):
                if f"person_{i}" == pid:
                    bbox = det.get_bbox()
                    cx = (bbox.xmin() + bbox.xmax()) / 2
                    break
            else:
                cx = 0.5
            pl, pitch, eq, vol, pan, sound_file = make_audio_pipeline(sound_to_play, pid, cx, 0)
            # Seek to start_position
            pl.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, start_position)
            audio_pipelines[pid] = (pl, pitch, eq, vol, pan, sound_file)
        else:
            # Update pan
            pan = audio_pipelines[pid][4]
            for i, det in enumerate(detections):
                if f"person_{i}" == pid:
                    bbox = det.get_bbox()
                    cx = (bbox.xmin() + bbox.xmax()) / 2
                    break
            else:
                cx = 0.5
            pan.set_property("panorama", 2 * cx - 1)

def run_visualisation(user_data):
    global current_visual_index, screen_state, tutorial_sound_on, is_fullscreen, screen, SCREEN_WIDTH, SCREEN_HEIGHT, HALF_SCREEN_WIDTH

    running = True
    while running:
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
                        if current_visual_index == 0:
                            tutorial_sound_on = not tutorial_sound_on
                        else:
                            current_visual_index = 0
                            tutorial_sound_on = True

        # Determine sound and people to play
        if screen_state in (0, 1):
            if current_visual_index == 0:
                if tutorial_sound_on and user_data.person_trails:
                    selected_person = next(iter(user_data.person_trails))
                    sound_to_play = os.path.join(os.getcwd(), "welcome.wav")
                    people_to_play = [selected_person]
                else:
                    sound_to_play = None
                    people_to_play = []
            else:
                sound_to_play = get_sound_path(current_visual_index)
                if sound_to_play and user_data.person_trails:
                    people_to_play = list(user_data.person_trails.keys())
                else:
                    people_to_play = []
        else:
            sound_to_play = None
            people_to_play = []

        # Update audio pipelines
        update_audio_per_person(user_data.detections, sound_to_play, people_to_play)

        # Render
        if screen_state == 0:  # Visual only
            if current_visual_index == 0:
                if people_to_play:
                    trails_to_draw = {people_to_play[0]: user_data.person_trails[people_to_play[0]]}
                else:
                    trails_to_draw = {}
                draw_line_trails(screen, trails_to_draw)
            else:
                visuals[current_visual_index].visualize(user_data, screen)
            overlay_text(visual_names[current_visual_index], 20, 20)
            overlay_text("Visual Only", SCREEN_WIDTH - 180, 20)
        elif screen_state == 1:  # Split-screen
            if current_visual_index == 0:
                if people_to_play:
                    trails_to_draw = {people_to_play[0]: user_data.person_trails[people_to_play[0]]}
                else:
                    trails_to_draw = {}
                draw_split_screen(user_data, trails_to_draw)
            else:
                draw_split_screen(user_data)
            overlay_text(visual_names[current_visual_index], 20, 20)
            overlay_text("Split-Screen", SCREEN_WIDTH - 200, 20)
        else:  # Frame + KP
            screen.fill(BG_COLOR)
            if user_data.frame is not None:
                frm = cv2.flip(cv2.resize(user_data.frame, (SCREEN_WIDTH, SCREEN_HEIGHT)), 1)
                screen.blit(pygame.surfarray.make_surface(np.rot90(frm)), (0, 0))
            overlay_text(f"Keypoints Mode ({'On' if show_keypoints else 'Off'})", SCREEN_WIDTH - 320, 20)

        pygame.display.flip()
        clock.tick(30)

    # Cleanup
    for pl, *_ in audio_pipelines.values():
        pl.set_state(Gst.State.NULL)
    pygame.quit()
    os._exit(0)

# Bootstrap
class UserData(app_callback_class):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.detections = []
        self.person_trails = {}

    def set_frame(self, f): self.frame = f
    def set_detections(self, d): self.detections = d

if __name__ == "__main__":
    class MotionTrailsVisual:
        def visualize(self, user_data, surface):
            draw_line_trails(surface, user_data.person_trails)
    visuals.insert(0, MotionTrailsVisual())
    visual_names.insert(0, "Motion Trails")
    load_visuals()

    user_data = UserData()
    app = GStreamerPoseEstimationApp(app_callback, user_data)
    threading.Thread(target=app.run, daemon=True).start()

    welcome_sound_path = os.path.join(os.getcwd(), "welcome.wav")
    if os.path.exists(welcome_sound_path):
        play_sound_once(welcome_sound_path)

    run_visualisation(user_data)
