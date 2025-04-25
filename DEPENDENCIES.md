# Wrist Motion Tracker with Pose Estimation and Sound Feedback

## Overview
This Python script visualizes the motion trails of a person’s wrists (left and right) using a pose estimation model on a Raspberry Pi with Hailo AI acceleration. It plays a sound when significant movement is detected. The GUI is powered by `pygame`, while the pose estimation pipeline is built using `GStreamer` and Hailo’s SDK.

---

## Dependencies

Make sure the following Python modules and tools are installed:

- `gi.repository.Gst`: GStreamer bindings for Python
- `pygame`: 2D graphics and sound
- `numpy`: Numerical computations
- `math`: Distance calculations
- `threading`: Handles concurrent execution of GStreamer and pygame
- `hailo`: Hailo AI SDK
- `hailo_apps_infra`: Utilities for working with Hailo pipelines


---

## Structure and Functionality

### 1. Initialization
- Initializes GStreamer, Pygame, and audio.
- Screen dimensions: `1280x720`.
- Loads default sound: `/usr/share/sounds/alsa/Front_Center.wav`.

### 2. Visual Components
- Motion trails are stored in:
  - `left_wrist_trail`
  - `right_wrist_trail`

#### `draw_motion_trails()`
- Clears the screen and redraws wrist trails.

#### `draw_trail(trail, color)`
- Draws lines between consecutive points in the trail.

### 3. Sound and Motion Logic
- **`MOVEMENT_THRESHOLD = 100`** (Euclidean distance)
  - If exceeded between consecutive points, sound is triggered.

#### `update_trail(trail, new_point, volume)`
- Adds new point to trail.
- Plays sound with volume based on bounding box height (proximity).

### 4. Pose Estimation & Callback Logic

#### `get_keypoints()`
- Returns index mapping for keypoint names from the model.

#### `app_callback()`
- GStreamer pad probe callback:
  - Extracts pose keypoints.
  - Tracks wrist positions.
  - Scales them to screen coordinates.
  - Calls `update_trail()` for each wrist.

### 5. Application Control

#### `run_visualization()`
- Main `pygame` loop.
- Handles ESC key and window close.
- Calls `draw_motion_trails()` at 30 FPS.

#### `main()`
- Initializes the app and callback handler.
- Launches GStreamer pipeline in a separate thread.
- Starts the visualization.
- Ensures proper cleanup on exit.

---

## 🔁 Execution Flow

1. `main()` is called.
2. GStreamer pipeline starts and listens for camera input.
3. Pygame window opens for real-time visualization.
4. On each frame:
   - Pose estimation is applied.
   - Wrist positions are tracked.
   - Movement is visualized.
   - If fast movement is detected → sound is played.
5. On exit (`ESC` key or window close):
   - GStreamer and Pygame shut down cleanly.
