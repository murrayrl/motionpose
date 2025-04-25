import pygame
import hailo
import random

class MotionTrailsMultipleVisual:
    def __init__(self):
        self.trails = {}  # {tracking_id: {'left_wrist': [], 'right_wrist': []}}
        self.colors = {}  # {tracking_id: (left_color, right_color)}
        self.max_trail_length = 30

    def visualize(self, user_data, surface):
        surface.fill((0, 0, 0))  # Clear the surface
        detections = user_data.detections
        if not detections:
            return

        for detection in detections:
            if detection.get_label() == "person" and detection.get_confidence() >= 0.5:
                # Get tracking ID or use a fallback
                track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
                tracking_id = track[0].get_id() if track else id(detection)

                # Initialize trails and colors for new people
                if tracking_id not in self.trails:
                    self.trails[tracking_id] = {'left_wrist': [], 'right_wrist': []}
                    self.colors[tracking_id] = (
                        (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255)),
                        (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
                    )

                # Get wrist landmarks
                landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                if landmarks:
                    points = landmarks[0].get_points()
                    left_wrist = points[9]  # Left wrist
                    right_wrist = points[10]  # Right wrist
                    width, height = surface.get_width(), surface.get_height()
                    left_pos = (int(left_wrist.x() * width), int(left_wrist.y() * height))
                    right_pos = (int(right_wrist.x() * width), int(right_wrist.y() * height))

                    # Update trails
                    self.trails[tracking_id]['left_wrist'].append(left_pos)
                    self.trails[tracking_id]['right_wrist'].append(right_pos)
                    if len(self.trails[tracking_id]['left_wrist']) > self.max_trail_length:
                        self.trails[tracking_id]['left_wrist'].pop(0)
                    if len(self.trails[tracking_id]['right_wrist']) > self.max_trail_length:
                        self.trails[tracking_id]['right_wrist'].pop(0)

        # Draw trails for all tracked people
        for tracking_id, trails in self.trails.items():
            left_color, right_color = self.colors[tracking_id]
            for i in range(1, len(trails['left_wrist'])):
                pygame.draw.line(surface, left_color, trails['left_wrist'][i-1], trails['left_wrist'][i], 5)
            for i in range(1, len(trails['right_wrist'])):
                pygame.draw.line(surface, right_color, trails['right_wrist'][i-1], trails['right_wrist'][i], 5)

VisualClass = MotionTrailsMultipleVisual
