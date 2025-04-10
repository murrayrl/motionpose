import pygame
import hailo  # Add this import

connections = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 9),
    (0, 6), (6, 8), (8, 10),
    (5, 11), (6, 12),
    (11, 12), (11, 13), (13, 15),
    (12, 14), (14, 16)
]

def visualize(user_data, screen):
    screen.fill((0, 0, 0))  # Clear screen

    keypoints = user_data.detections
    if not keypoints:
        return

    for detection in keypoints:
        if detection.get_label() == "person":
            points = detection.get_objects_typed(hailo.HAILO_LANDMARKS)[0].get_points()  # Use enum
            scaled_points = [(int(p.x() * screen.get_width()), int(p.y() * screen.get_height())) for p in points]

            for p1, p2 in connections:
                pygame.draw.line(screen, (0, 255, 255), scaled_points[p1], scaled_points[p2], 3)
