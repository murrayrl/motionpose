#!/usr/bin/env python3
# FINAL.py – multi-person pose-audio visualiser (motion-trail bug fixed)

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
import os, threading, importlib.util, cv2, numpy as np, pygame, hailo
from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad, get_numpy_from_buffer, app_callback_class
)
from hailo_apps_infra.pose_estimation_pipeline import GStreamerPoseEstimationApp

# ────────── init ──────────
Gst.init(None)
pygame.init()
pygame.mixer.quit()                           # let GStreamer own audio
is_fullscreen   = True
screen          = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SCREEN_W, SCREEN_H = screen.get_size()
HALF_W          = SCREEN_W // 2
clock           = pygame.time.Clock()
font            = pygame.font.Font(None, 36)

# ────────── constants ──────────
BG, TXT          = (0, 0, 0), (255, 255, 0)
LEFT_CLR, RIGHT_CLR = (0, 255, 0), (0, 0, 255)
BBOX_CLR         = (255, 255, 0)
CONF_THR         = 0.5
TRAIL_LEN        = 30

# ────────── globals ──────────
visuals, visual_names = [], []
cur_vis   = 0
mode      = 1                      # 0 visual | 1 split | 2 frame+keypts
tutorial_sound_on = True

audio_pipelines = {}               # pid → (pl, pitch, eq, vol, pan, file)
cur_sound       = None
welcome_pipeline = None
welcome_played   = False

# ────────── audio helpers ──────────
def sound_path(idx:int)->str|None:
    stem = visual_names[idx].replace(' ', '') + "Visual.wav"
    p = os.path.join(os.getcwd(), "normalized_sounds", stem)
    return p if os.path.exists(p) else None

def make_audio(sound_file:str, pid:str, xpos:float):
    pl = Gst.Pipeline.new(pid)
    mk = lambda name: Gst.ElementFactory.make(name, None)
    fs, dec  = mk("filesrc"), mk("decodebin")
    ac, ar   = mk("audioconvert"), mk("audioresample")
    pitch, pan = mk("pitch"), mk("audiopanorama")
    eq, vol, sink = mk("equalizer-10bands"), mk("volume"), mk("autoaudiosink")
    for e in (fs, dec, ac, ar, pitch, pan, eq, vol, sink): pl.add(e)
    fs.set_property("location", sound_file)
    fs.link(dec)
    dec.connect("pad-added", lambda _, p: p.link(ac.get_static_pad("sink")))
    ac.link(ar); ar.link(pitch); pitch.link(pan)
    pan.link(eq); eq.link(vol); vol.link(sink)

    vis = visual_names[cur_vis]
    if vis == "FeetHeatmap": eq.set_property("band0", 6.0); eq.set_property("band1", 6.0)
    elif vis == "HipCircles": vol.set_property("volume", 0.8)
    elif vis == "Skeleton": pitch.set_property("pitch", 1.05)

    pan.set_property("panorama", 2*xpos - 1)
    def bus_cb(_, msg):
        if msg.type == Gst.MessageType.EOS:
            pl.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH|Gst.SeekFlags.KEY_UNIT, 0)
        elif msg.type == Gst.MessageType.ERROR:
            pl.set_state(Gst.State.NULL)
    pl.get_bus().add_signal_watch()
    pl.get_bus().connect("message", bus_cb)
    pl.set_state(Gst.State.PLAYING)
    return pl, pitch, eq, vol, pan, sound_file

def play_once(path:str):
    global welcome_pipeline
    pl=Gst.parse_launch(f'filesrc location="{path}" ! decodebin ! audioconvert ! autoaudiosink')
    def cb(_,m): 
        if m.type in (Gst.MessageType.EOS, Gst.MessageType.ERROR):
            pl.set_state(Gst.State.NULL)
    pl.get_bus().add_signal_watch(); pl.get_bus().connect("message", cb)
    pl.set_state(Gst.State.PLAYING); welcome_pipeline=pl

# ────────── draw helpers ──────────
def draw_trails(surf, trails:dict):
    surf.fill(BG); w,h = surf.get_size()
    for kpmap in trails.values():
        for key,col in (("left_wrist",LEFT_CLR),("right_wrist",RIGHT_CLR)):
            seq=kpmap.get(key,[])
            if len(seq)<2: continue
            pts=[(int(x*w),int(y*h)) for x,y in seq]
            pygame.draw.lines(surf,col,False,pts,5)

def split_screen(ud):
    screen.fill(BG)
    left = screen.subsurface((0,0,HALF_W,SCREEN_H)); left.fill(BG)
    visuals[cur_vis].visualize(ud,left)

    if ud.frame is not None:
        frm=cv2.flip(cv2.resize(ud.frame,(HALF_W,SCREEN_H)),1)
        screen.blit(pygame.surfarray.make_surface(np.rot90(frm)),(HALF_W,0))
        for d in ud.detections:
            if d.get_label()!="person" or d.get_confidence()<CONF_THR: continue
            b=d.get_bbox()
            x1=HALF_W+int(b.xmin()*HALF_W); y1=int(b.ymin()*SCREEN_H)
            x2=HALF_W+int(b.xmax()*HALF_W); y2=int(b.ymax()*SCREEN_H)
            pygame.draw.rect(screen,BBOX_CLR,(x1,y1,x2-x1,y2-y1),2)

def txt(t,x=20,y=20):
    screen.blit(font.render(t,True,TXT),(x,y))

# ────────── gst callback ──────────
def gst_cb(pad,info,ud):
    buf=info.get_buffer(); ud.increment()
    fmt,w,h=get_caps_from_pad(pad)
    if fmt and w and h:
        ud.set_frame(cv2.cvtColor(get_numpy_from_buffer(buf,fmt,w,h),cv2.COLOR_RGB2BGR))
    roi = hailo.get_roi_from_buffer(buf)
    dets= roi.get_objects_typed(hailo.HAILO_DETECTION)
    seen=set()
    for i,d in enumerate(dets):
        if d.get_label()!="person" or d.get_confidence()<CONF_THR: continue
        pid=f"person_{i}"; seen.add(pid)
        trailmap=ud.person_trails.setdefault(pid,{})
        lms=d.get_objects_typed(hailo.HAILO_LANDMARKS)
        if not lms: continue
        pts=lms[0].get_points()
        for idx,label in ((9,"left_wrist"),(10,"right_wrist")):
            if idx>=len(pts): continue
            seq=trailmap.setdefault(label,[])
            seq.append((pts[idx].x(),pts[idx].y()))
            if len(seq)>TRAIL_LEN: seq.pop(0)
    # prune vanished people
    for pid in list(ud.person_trails):
        if pid not in seen: del ud.person_trails[pid]
    ud.set_detections(dets)
    return Gst.PadProbeReturn.OK

# ────────── audio sync ──────────
def sync_audio(dets,snd,people):
    global cur_sound,audio_pipelines
    if snd!=cur_sound:
        for pl,*_ in audio_pipelines.values(): pl.set_state(Gst.State.NULL)
        audio_pipelines.clear(); cur_sound=snd
    for pid in list(audio_pipelines):
        if pid not in people:
            audio_pipelines[pid][0].set_state(Gst.State.NULL); del audio_pipelines[pid]
    for pid in people:
        if pid in audio_pipelines: continue
        cx=0.5
        for i,d in enumerate(dets):
            if f"person_{i}"==pid:
                b=d.get_bbox(); cx=(b.xmin()+b.xmax())/2; break
        pl,*rest=make_audio(snd,pid,cx)
        audio_pipelines[pid]=(pl,*rest)

# ────────── main loop ──────────
def loop(ud):
    global cur_vis,mode,is_fullscreen,SCREEN_W,SCREEN_H,HALF_W,welcome_played,welcome_pipeline,tutorial_sound_on
    show_kp=True; running=True
    while running:
        for e in pygame.event.get():
            if e.type==pygame.QUIT or (e.type==pygame.KEYDOWN and e.key==pygame.K_q): running=False
            elif e.type==pygame.KEYDOWN:
                match e.key:
                    case pygame.K_RIGHT: mode=(mode+1)%3
                    case pygame.K_LEFT:  mode=(mode-1)%3
                    case pygame.K_UP   if visuals: cur_vis=(cur_vis+1)%len(visuals)
                    case pygame.K_DOWN if visuals: cur_vis=(cur_vis-1)%len(visuals)
                    case pygame.K_k: show_kp=not show_kp
                    case pygame.K_p:
                        is_fullscreen=not is_fullscreen
                        screen_mode=pygame.FULLSCREEN if is_fullscreen else 0
                        size=(0,0) if is_fullscreen else (1280,720)
                        screen.__setattr__('screen', pygame.display.set_mode(size,screen_mode))
                        SCREEN_W,SCREEN_H=screen.get_size(); HALF_W=SCREEN_W//2
                    case pygame.K_t:
                        if cur_vis==0:
                            tutorial_sound_on=not tutorial_sound_on
                            welcome_played=False
                            if welcome_pipeline: welcome_pipeline.set_state(Gst.State.NULL); welcome_pipeline=None
                        else:
                            cur_vis=0; tutorial_sound_on=True; welcome_played=False
                            if welcome_pipeline: welcome_pipeline.set_state(Gst.State.NULL); welcome_pipeline=None
        # decide snd
        person_ids=list(ud.person_trails.keys())
        if mode in (0,1):
            if cur_vis==0 and tutorial_sound_on and person_ids and not welcome_played and not welcome_pipeline:
                wp=os.path.join(os.getcwd(),"welcome.wav")
                if os.path.exists(wp): play_once(wp); welcome_played=True
                snd=None; play=[]
            else:
                snd=sound_path(cur_vis); play=person_ids if snd else []
        else: snd=None; play=[]
        sync_audio(ud.detections,snd,play)

        # draw
        if mode==0:
            screen.fill(BG); visuals[cur_vis].visualize(ud,screen)
            txt(visual_names[cur_vis]); txt("Visual-Only",SCREEN_W-180)
        elif mode==1:
            split_screen(ud)
            txt(visual_names[cur_vis]); txt("Split",SCREEN_W-100)
        else:
            screen.fill(BG)
            if ud.frame is not None:
                frm=cv2.flip(cv2.resize(ud.frame,(SCREEN_W,SCREEN_H)),1)
                screen.blit(pygame.surfarray.make_surface(np.rot90(frm)),(0,0))
                for d in ud.detections:
                    if d.get_label()!="person" or d.get_confidence()<CONF_THR: continue
                    b=d.get_bbox()
                    x1,y1 = int(b.xmin()*SCREEN_W),int(b.ymin()*SCREEN_H)
                    x2,y2 = int(b.xmax()*SCREEN_W),int(b.ymax()*SCREEN_H)
                    pygame.draw.rect(screen,BBOX_CLR,(x1,y1,x2-x1,y2-y1),2)
                    if show_kp:
                        lms=d.get_objects_typed(hailo.HAILO_LANDMARKS)
                        if lms:
                            for p in lms[0].get_points():
                                pygame.draw.circle(screen,(255,0,0),(int(p.x()*SCREEN_W),int(p.y()*SCREEN_H)),3)
            txt(f"Keypoints {'On' if show_kp else 'Off'}",SCREEN_W-250)
        pygame.display.flip(); clock.tick(30)

    if welcome_pipeline: welcome_pipeline.set_state(Gst.State.NULL)
    for pl,*_ in audio_pipelines.values(): pl.set_state(Gst.State.NULL)
    pygame.quit(); os._exit(0)

# ────────── userdata ──────────
class UD(app_callback_class):
    def __init__(self):
        super().__init__(); self.frame=None; self.detections=[]; self.person_trails={}
    def set_frame(self,f): self.frame=f
    def set_detections(self,d): self.detections=d

# ────────── visuals ──────────
def load_visuals():
    d="multi_person_visuals"
    if not os.path.isdir(d): return
    for f in os.listdir(d):
        if not f.endswith(".py"): continue
        modname=f[:-3]
        spec=importlib.util.spec_from_file_location(modname,os.path.join(d,f))
        m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        if hasattr(m,"VisualClass"):
            visuals.append(m.VisualClass())
            visual_names.append(modname.replace("Visual",""))

class MotionTrails:
    def visualize(self,ud,surf): draw_trails(surf,ud.person_trails)

# ────────── main ──────────
if __name__=="__main__":
    visuals.append(MotionTrails()); visual_names.append("Motion Trails")
    load_visuals()
    ud=UD()
    app=GStreamerPoseEstimationApp(gst_cb,ud)
    threading.Thread(target=app.run,daemon=True).start()
    loop(ud)

