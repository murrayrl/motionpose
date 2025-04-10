import pygame
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
                    left_hip = points[11]  # Left hip
                    right_hip = points[12]  # Right hip
                    width, height = surface.get_width(), surface.get_height()
                    hip_x = int((left_hip.x() + right_hip.x()) / 2 * width)
                    hip_y = int((left_hip.y() + right_hip.y()) / 2 * height)

                    radius = 20 + int(10 * math.sin(pygame.time.get_ticks() * 0.01))
                    pygame.draw.circle(surface, self.colors[tracking_id], (hip_x, hip_y), radius, 3)

VisualClass = HipCirclesVisual
