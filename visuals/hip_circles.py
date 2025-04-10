import pygame
import hailo  # Add this import
import math

def visualize(user_data, screen):
    screen.fill((0, 0, 0))  # Clear screen

    keypoints = user_data.detections
    if not keypoints:
        return

    for detection in keypoints:
        if detection.get_label() == "person":
            points = detection.get_objects_typed(hailo.HAILO_LANDMARKS)[0].get_points()  # Use enum
            left_hip = points[11]
            right_hip = points[12]

            hip_x = int((left_hip.x() + right_hip.x()) / 2 * screen.get_width())
            hip_y = int((left_hip.y() + right_hip.y()) / 2 * screen.get_height())

            radius = 20 + int(10 * math.sin(pygame.time.get_ticks() * 0.01))
            pygame.draw.circle(screen, (0, 255, 0), (hip_x, hip_y), radius, 3)
