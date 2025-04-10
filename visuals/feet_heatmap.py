import pygame
import hailo  # Add this import

feet_positions = []

def visualize(user_data, screen):
    global feet_positions
    screen.fill((0, 0, 0))  # Clear screen

    keypoints = user_data.detections
    if not keypoints:
        return

    for detection in keypoints:
        if detection.get_label() == "person":
            points = detection.get_objects_typed(hailo.HAILO_LANDMARKS)[0].get_points()  # Use enum
            left_ankle = points[15]
            right_ankle = points[16]

            feet_positions.append((int(left_ankle.x() * screen.get_width()), int(left_ankle.y() * screen.get_height())))
            feet_positions.append((int(right_ankle.x() * screen.get_width()), int(right_ankle.y() * screen.get_height())))

    if len(feet_positions) > 500:
        feet_positions.pop(0)

    for i, (x, y) in enumerate(feet_positions):
        alpha = max(255 - (len(feet_positions) - i) * 5, 50)
        pygame.draw.circle(screen, (255, 0, 0, alpha), (x, y), 10)
