import pygame
import hailo  # Add this import

def visualize(user_data, screen):
    screen.fill((0, 0, 0))  # Clear screen

    keypoints = user_data.detections
    if not keypoints:
        return

    for detection in keypoints:
        if detection.get_label() == "person":
            points = detection.get_objects_typed(hailo.HAILO_LANDMARKS)[0].get_points()  # Use enum
            neck = points[0]
            left_hip = points[11]
            right_hip = points[12]

            mid_hip_x = (left_hip.x() + right_hip.x()) / 2
            mid_hip_y = (left_hip.y() + right_hip.y()) / 2

            pygame.draw.line(
                screen, (0, 255, 255),
                (int(neck.x() * screen.get_width()), int(neck.y() * screen.get_height())),
                (int(mid_hip_x * screen.get_width()), int(mid_hip_y * screen.get_height())),
                5
            )
