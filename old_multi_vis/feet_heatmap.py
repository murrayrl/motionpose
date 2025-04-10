import pygame
import hailo
import random

class FeetHeatmapVisual:
    def __init__(self):
        self.positions = {}  # {tracking_id: [(x, y), ...]}
        self.colors = {}  # {tracking_id: color}
        self.max_positions = 500

    def visualize(self, user_data, surface):
        surface.fill((0, 0, 0))  # Clear the surface
        detections = user_data.detections
        if not detections:
            return

        for detection in detections:
            if detection.get_label() == "person" and detection.get_confidence() >= 0.5:
                tracking_id = detection.get_tracking_id()
                if tracking_id not in self.positions:
                    self.positions[tracking_id] = []
                    self.colors[tracking_id] = (
                        random.randint(100, 255),
                        random.randint(100, 255),
                        random.randint(100, 255)
                    )

                landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                if landmarks:
                    points = landmarks[0].get_points()
                    left_ankle = points[15]  # Left ankle
                    right_ankle = points[16]  # Right ankle
                    width, height = surface.get_width(), surface.get_height()
                    left_pos = (int(left_ankle.x() * width), int(left_ankle.y() * height))
                    right_pos = (int(right_ankle.x() * width), int(right_ankle.y() * height))

                    self.positions[tracking_id].append(left_pos)
                    self.positions[tracking_id].append(right_pos)
                    if len(self.positions[tracking_id]) > self.max_positions:
                        self.positions[tracking_id].pop(0)

        for tracking_id, pos_list in self.positions.items():
            color = self.colors[tracking_id]
            for i, pos in enumerate(pos_list):
                alpha = max(255 - (len(pos_list) - i) * 5, 50)
                pygame.draw.circle(surface, color + (alpha,), pos, 10)

VisualClass = FeetHeatmapVisual
