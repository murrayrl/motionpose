import pygame
import hailo
import random

class ElbowTrailsVisual:
    def __init__(self):
        self.trails = {}  # {tracking_id: {'left': [], 'right': []}}
        self.colors = {}  # {tracking_id: (left_color, right_color)}
        self.trail_length = 30

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

                if tracking_id not in self.trails:
                    self.trails[tracking_id] = {'left': [], 'right': []}
                    self.colors[tracking_id] = (
                        (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)),
                        (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
                    )

                landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                if landmarks:
                    points = landmarks[0].get_points()
                    left_elbow = points[7]  # Left elbow
                    right_elbow = points[8]  # Right elbow
                    width, height = surface.get_width(), surface.get_height()
                    left_pos = (int(left_elbow.x() * width), int(left_elbow.y() * height))
                    right_pos = (int(right_elbow.x() * width), int(right_elbow.y() * height))

                    self.trails[tracking_id]['left'].append(left_pos)
                    self.trails[tracking_id]['right'].append(right_pos)
                    if len(self.trails[tracking_id]['left']) > self.trail_length:
                        self.trails[tracking_id]['left'].pop(0)
                    if len(self.trails[tracking_id]['right']) > self.trail_length:
                        self.trails[tracking_id]['right'].pop(0)

        for tracking_id, trails in self.trails.items():
            left_color, right_color = self.colors[tracking_id]
            for i in range(1, len(trails['left'])):
                pygame.draw.line(surface, left_color, trails['left'][i-1], trails['left'][i], 5)
            for i in range(1, len(trails['right'])):
                pygame.draw.line(surface, right_color, trails['right'][i-1], trails['right'][i], 5)

VisualClass = ElbowTrailsVisual
