import pygame
import hailo
import random

class SpineLineVisual:
    def __init__(self):
        self.colors = {}  # {tracking_id: color}

    def visualize(self, user_data, surface):
        surface.fill((0, 0, 0))  # Clear the surface
        detections = user_data.detections
        if not detections:
            return

        for detection in detections:
            if detection.get_label() == "person" and detection.get_confidence() >= 0.5:
                # Try to get tracking ID; use fallback if not available
                track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
                if track:
                    tracking_id = track[0].get_id()
                else:
                    tracking_id = id(detection)  # Temporary ID if tracking is not enabled

                if tracking_id not in self.colors:
                    self.colors[tracking_id] = (
                        random.randint(100, 255),
                        random.randint(100, 255),
                        random.randint(100, 255)
                    )

                landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                if landmarks:
                    points = landmarks[0].get_points()
                    neck = points[0]  # Neck (nose or midpoint)
                    left_hip = points[11]
                    right_hip = points[12]
                    mid_hip_x = (left_hip.x() + right_hip.x()) / 2
                    mid_hip_y = (left_hip.y() + right_hip.y()) / 2
                    width, height = surface.get_width(), surface.get_height()
                    neck_pos = (int(neck.x() * width), int(neck.y() * height))
                    hip_pos = (int(mid_hip_x * width), int(mid_hip_y * height))

                    pygame.draw.line(surface, self.colors[tracking_id], neck_pos, hip_pos, 5)

VisualClass = SpineLineVisual
