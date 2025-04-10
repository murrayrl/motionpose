import pygame
import hailo
import random

class SkeletonVisual:
    def __init__(self):
        self.colors = {}  # {tracking_id: color}
        self.connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),  # Head
            (0, 5), (5, 6), (6, 7), (7, 9),  # Left arm
            (0, 6), (6, 8), (8, 10),  # Right arm
            (5, 11), (6, 12),  # Shoulders to hips
            (11, 12), (11, 13), (13, 15),  # Left leg
            (12, 14), (14, 16)  # Right leg
        ]

    def visualize(self, user_data, surface):
        surface.fill((0, 0, 0))  # Clear the surface
        detections = user_data.detections
        if not detections:
            return

        for detection in detections:
            if detection.get_label() == "person" and detection.get_confidence() >= 0.5:
                tracking_id = detection.get_tracking_id()
                if tracking_id not in self.colors:
                    self.colors[tracking_id] = (
                        random.randint(100, 255),
                        random.randint(100, 255),
                        random.randint(100, 255)
                    )

                landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                if landmarks:
                    points = landmarks[0].get_points()
                    width, height = surface.get_width(), surface.get_height()
                    scaled_points = [(int(p.x() * width), int(p.y() * height)) for p in points]

                    for p1, p2 in self.connections:
                        pygame.draw.line(surface, self.colors[tracking_id], scaled_points[p1], scaled_points[p2], 3)

VisualClass = SkeletonVisual
