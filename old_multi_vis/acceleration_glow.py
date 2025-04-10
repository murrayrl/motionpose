import pygame
import hailo
import random

class AccelerationGlowVisual:
    def __init__(self):
        self.trails = {}  # {tracking_id: {'wrist': []}}
        self.colors = {}  # {tracking_id: color}
        self.max_trail_length = 30

    def visualize(self, user_data, surface):
        surface.fill((0, 0, 0))  # Clear the surface
        detections = user_data.detections
        if not detections:
            return

        for detection in detections:
            if detection.get_label() == "person" and detection.get_confidence() >= 0.5:
                tracking_id = detection.get_tracking_id()
                if tracking_id not in self.trails:
                    self.trails[tracking_id] = {'wrist': []}
                    self.colors[tracking_id] = (
                        random.randint(100, 255),
                        random.randint(100, 255),
                        random.randint(100, 255)
                    )

                landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
                if landmarks:
                    points = landmarks[0].get_points()
                    wrist = points[9]  # Left wrist
                    width, height = surface.get_width(), surface.get_height()
                    new_pos = (int(wrist.x() * width), int(wrist.y() * height))

                    if len(self.trails[tracking_id]['wrist']) > 0:
                        prev_pos = self.trails[tracking_id]['wrist'][-1]
                        speed = ((new_pos[0] - prev_pos[0]) ** 2 + (new_pos[1] - prev_pos[1]) ** 2) ** 0.5
                        alpha = min(int(speed * 10), 255)
                        color = self.colors[tracking_id] + (alpha,)
                        pygame.draw.circle(surface, color, new_pos, 10)

                    self.trails[tracking_id]['wrist'].append(new_pos)
                    if len(self.trails[tracking_id]['wrist']) > self.max_trail_length:
                        self.trails[tracking_id]['wrist'].pop(0)

VisualClass = AccelerationGlowVisual
