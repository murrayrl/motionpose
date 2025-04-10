import pygame
import hailo  # Add this import

trail_length = 30
left_elbow_trail = []
right_elbow_trail = []

def visualize(user_data, screen):
    screen.fill((0, 0, 0))  # Clear screen

    keypoints = user_data.detections
    if not keypoints:
        return

    for detection in keypoints:
        if detection.get_label() == "person":
            points = detection.get_objects_typed(hailo.HAILO_LANDMARKS)[0].get_points()  # Use enum
            left_elbow = points[7]
            right_elbow = points[8]

            left_elbow_trail.append((int(left_elbow.x() * screen.get_width()), int(left_elbow.y() * screen.get_height())))
            right_elbow_trail.append((int(right_elbow.x() * screen.get_width()), int(right_elbow.y() * screen.get_height())))

    if len(left_elbow_trail) > trail_length:
        left_elbow_trail.pop(0)
    if len(right_elbow_trail) > trail_length:
        right_elbow_trail.pop(0)

    for i in range(len(left_elbow_trail) - 1):
        pygame.draw.line(screen, (255, 255, 0), left_elbow_trail[i], left_elbow_trail[i + 1], 5)
        pygame.draw.line(screen, (255, 165, 0), right_elbow_trail[i], right_elbow_trail[i + 1], 5)
