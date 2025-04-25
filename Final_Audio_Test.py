import gi
import os
import numpy as np
import pygame
import hailo
import threading
import cv2
import importlib.util
from gi.repository import Gst
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

# Screen setup
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_width(), screen.get_height()
HALF_SCREEN_WIDTH = SCREEN_WIDTH // 2
pygame.display.set_caption("Enhanced Pose Estimation with Audio")

clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)

# Visualization settings
enabled_visuals = []
visual_names = []
current_visual_index = 0
screen_state = 1  # 0=visual-only,1=split,2=kpts+bbox
confidence_threshold = 0.5
show_keypoints = True
is_fullscreen = True

# Motion trail storage
trail_length = 30
person_trails = {}

# LUFS values for each sound file
lufs_values = {
    "AccelerationGlowVisual.wav": -24.18,
    "ElbowTrailsVisual.wav": -26.72,
    "FeetHeatmapVisual.wav": -43.33,
    "HipCirclesVisual.wav": -17.93,
    "SkeletonVisual.wav": -12.23,
    "SpineLineVisual.wav": -20.67,
}

# Precompute volume multipliers to normalize to -23 LUFS
volume_multipliers = {
    fname: (10 ** ((-23.0 - lufs) / 20) if lufs < -23.0 else 1.0)
    for fname, lufs in lufs_values.items()
}

def create_audio_pipeline(sound_file):
    """Create a simple GStreamer playbin pipeline for audio playback."""
    sound_path = os.path.abspath(sound_file)
    if not os.path.isfile(sound_path):
        raise FileNotFoundError(f"Sound file not found: {sound_path}")
    uri = 'file://' + sound_path

    pipeline = Gst.parse_launch(f"playbin uri={uri}")
    # Set normalized volume
    base_name = os.path.basename(sound_file)
    volume = volume_multipliers.get(base_name, 1.0)
    pipeline.set_property("volume", volume)

    # Watch for errors
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    def on_message(bus, message):
        if message.type == Gst.MessageType.ERROR:
            err, dbg = message.parse_error()
            print(f"GStreamer Error: {err}, Debug: {dbg}")
    bus.connect("message", on_message)

    return pipeline

# Load visuals dynamically
def load_visuals():
    visuals_dir = "multi_person_visuals"
    if os.path.isdir(visuals_dir):
        for file in os.listdir(visuals_dir):
            if file.endswith('.py'):
                name = file[:-3]
                path = os.path.join(visuals_dir, file)
                spec = importlib.util.spec_from_file_location(name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'VisualClass'):
                    enabled_visuals.append(module.VisualClass())
                    display_name = name.replace('Visual', '').replace('_', ' ').title()
                    visual_names.append(display_name)

# Drawing helpers
def draw_trail(screen, trail, color):
    if len(trail) < 2:
        return
    w, h = screen.get_width(), screen.get_height()
    for i in range(len(trail) - 1):
        x1, y1 = int(trail[i][0] * w), int(trail[i][1] * h)
        x2, y2 = int(trail[i+1][0] * w), int(trail[i+1][1] * h)
        pygame.draw.line(screen, color, (x1, y1), (x2, y2), 5)

def draw_motion_trails(user_data, screen):
    screen.fill((0,0,0))
    for trails in person_trails.values():
        draw_trail(screen, trails.get('left_wrist', []), (0,255,0))
        draw_trail(screen, trails.get('right_wrist', []), (0,0,255))

def display_visual_name(name, is_default=False):
    text = name + (' - Single Person' if is_default else '')
    surf = font.render(text, True, (255,255,0))
    screen.blit(surf, (20,20))

def display_mode_text(mode):
    surf = font.render(mode, True, (255,255,0))
    x = SCREEN_WIDTH - surf.get_width() - 20
    screen.blit(surf, (x,20))

def draw_keypoints_and_bbox(user_data, screen):
    screen.fill((0,0,0))
    if user_data.frame is not None:
        frame = cv2.resize(user_data.frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
        frame = cv2.flip(frame,1)
        frame = np.rot90(frame)
        surf = pygame.surfarray.make_surface(frame)
        screen.blit(surf, (0,0))
        for det in user_data.detections:
            if det.get_label()=='person' and det.get_confidence()>=confidence_threshold:
                bbox = det.get_bbox()
                x1,y1 = int(bbox.xmin()*SCREEN_WIDTH), int(bbox.ymin()*SCREEN_HEIGHT)
                x2,y2 = int(bbox.xmax()*SCREEN_WIDTH), int(bbox.ymax()*SCREEN_HEIGHT)
                pygame.draw.rect(screen, (255,255,0),(x1,y1,x2-x1,y2-y1),2)
                if show_keypoints:
                    lms = det.get_objects_typed(hailo.HAILO_LANDMARKS)
                    if lms:
                        for pt in lms[0].get_points():
                            x,y = int(pt.x()*SCREEN_WIDTH), int(pt.y()*SCREEN_HEIGHT)
                            pygame.draw.circle(screen, (255,0,0),(x,y),3)

def draw_split_screen(user_data, screen):
    screen.fill((0,0,0))
    # left: visual
    if enabled_visuals:
        left = screen.subsurface((0,0,HALF_SCREEN_WIDTH,SCREEN_HEIGHT))
        enabled_visuals[current_visual_index].visualize(user_data, left)
    # right: live frame
    if user_data.frame is not None:
        frame = cv2.resize(user_data.frame,(HALF_SCREEN_WIDTH,SCREEN_HEIGHT))
        frame = cv2.flip(frame,1)
        frame = np.rot90(frame)
        surf = pygame.surfarray.make_surface(frame)
        screen.blit(surf,(HALF_SCREEN_WIDTH,0))

        # optional bbox on right side
        for det in user_data.detections:
            if det.get_label()=='person' and det.get_confidence()>=confidence_threshold:
                bbox=det.get_bbox()
                x1=int(bbox.xmin()*HALF_SCREEN_WIDTH)+HALF_SCREEN_WIDTH
                y1=int(bbox.ymin()*SCREEN_HEIGHT)
                x2=int(bbox.xmax()*HALF_SCREEN_WIDTH)+HALF_SCREEN_WIDTH
                y2=int(bbox.ymax()*SCREEN_HEIGHT)
                pygame.draw.rect(screen,(255,255,0),(x1,y1,x2-x1,y2-y1),2)

def get_person_count(user_data):
    return sum(1 for d in user_data.detections if d.get_label()=='person' and d.get_confidence()>=confidence_threshold)

# Trail update

def update_trail(trail, pt):
    trail.append(pt)
    if len(trail)>trail_length:
        trail.pop(0)

# Speed computation

def calculate_speed(prev_pt, cur_pt):
    return math.hypot(cur_pt[0]-prev_pt[0], cur_pt[1]-prev_pt[1])

# GStreamer pad probe callback

def app_callback(pad, info, user_data):
    buf = info.get_buffer()
    if buf is None:
        return Gst.PadProbeReturn.OK
    user_data.increment()
    fmt, w, h = get_caps_from_pad(pad)
    if fmt and w and h:
        arr = get_numpy_from_buffer(buf, fmt, w, h)
        frame = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)
    # handle detections
    roi = hailo.get_roi_from_buffer(buf)
    dets = roi.get_objects_typed(hailo.HAILO_DETECTION)
    # reset trails for each frame
    for pid in list(person_trails.keys()):
        person_trails[pid] = person_trails[pid]
    for idx, det in enumerate(dets):
        if det.get_label()=='person' and det.get_confidence()>=confidence_threshold:
            pid = f"person_{idx}"
            if pid not in person_trails:
                person_trails[pid] = {}
            lms = det.get_objects_typed(hailo.HAILO_LANDMARKS)
            if lms:
                pts = lms[0].get_points()
                for key,i in [('left_wrist',9),('right_wrist',10),('left_elbow',7),('right_elbow',8)]:
                    if len(pts)>i:
                        coord=(pts[i].x(),pts[i].y())
                        trail = person_trails[pid].get(key,[])
                        update_trail(trail,coord)
                        person_trails[pid][key]=trail
    user_data.set_detections(dets)
    return Gst.PadProbeReturn.OK

# Example visual class
class MotionTrailsVisual:
    def visualize(self, user_data, surface):
        draw_motion_trails(user_data, surface)

# Main loop
def run_visualization(user_data):
    global screen_state, current_visual_index, show_keypoints, is_fullscreen
    running=True
    audio_pipelines={}
    current_sound_file=None
    while running:
        for e in pygame.event.get():
            if e.type==pygame.QUIT or (e.type==pygame.KEYDOWN and e.key==pygame.K_q):
                running=False
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_RIGHT:
                    screen_state=(screen_state+1)%3
                elif e.key==pygame.K_LEFT:
                    screen_state=(screen_state-1)%3
                elif e.key==pygame.K_k:
                    show_keypoints=not show_keypoints
                elif e.key==pygame.K_p:
                    is_fullscreen=not is_fullscreen
                    if is_fullscreen:
                        screen=pygame.display.set_mode((0,0),pygame.FULLSCREEN)
                    else:
                        screen=pygame.display.set_mode((1280,720))
                    global SCREEN_WIDTH, SCREEN_HEIGHT, HALF_SCREEN_WIDTH
                    SCREEN_WIDTH,SCREEN_HEIGHT=screen.get_size()
                    HALF_SCREEN_WIDTH=SCREEN_WIDTH//2
        # audio logic
        pc=get_person_count(user_data)
        if screen_state in [0,1] and pc>0:
            fname=visual_names[current_visual_index].replace(' ','_').lower()+'.wav'
            sp=os.path.join('sounds',fname)
            new_sf=sp if os.path.isfile(sp) else None
        else:
            new_sf=None
        if new_sf!=current_sound_file:
            for p in audio_pipelines.values(): p.set_state(Gst.State.NULL)
            audio_pipelines.clear()
            if new_sf:
                for idx,det in enumerate(user_data.detections):
                    if det.get_label()=='person' and det.get_confidence()>=confidence_threshold:
                        pid=f'person_{idx}'
                        key=f"{pid}_{new_sf}"
                        pipe=create_audio_pipeline(new_sf)
                        pipe.set_state(Gst.State.PLAYING)
                        audio_pipelines[key]=pipe
            current_sound_file=new_sf
        # render
        if screen_state==0:
            enabled_visuals[current_visual_index].visualize(user_data,screen)
            display_visual_name(visual_names[current_visual_index],current_visual_index==0)
            display_mode_text('Visual Only')
        elif screen_state==1:
            draw_split_screen(user_data,screen)
            display_visual_name(visual_names[current_visual_index],current_visual_index==0)
            display_mode_text('Split-Screen')
        else:
            draw_keypoints_and_bbox(user_data,screen)
            display_mode_text(f'KPs: {"On" if show_keypoints else "Off"}')
        pygame.display.flip()
        clock.tick(30)
    # cleanup
    for p in audio_pipelines.values(): p.set_state(Gst.State.NULL)
    pygame.quit()
    os._exit(0)

if __name__=='__main__':
    enabled_visuals.insert(0, MotionTrailsVisual())
    visual_names.insert(0, 'Motion Trails')
    load_visuals()

    class user_app_callback_class(app_callback_class):
        def __init__(self):
            super().__init__()
            self.frame=None
            self.detections=[]
        def set_frame(self,f): self.frame=f
        def set_detections(self,det): self.detections=det

    user_data=user_app_callback_class()
    app=GStreamerPoseEstimationApp(app_callback, user_data)
    gst_thread=threading.Thread(target=app.run,daemon=True)
    gst_thread.start()
    run_visualization(user_data)
