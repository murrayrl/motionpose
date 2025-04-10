import pygame
import hailo  # Add this import

trail = []
max_trail_length = 30

def visualize(user_data, screen):
    global trail
    screen.fill((0, 0, 0))  # Clear screen

    keypoints = user_data.detections
    if not keypoints:
        return

    for detection in keypoints:
        if detection.get_label() == "person":
            points = detection.get_objects_typed(hailo.HAILO_LANDMARKS)[0].get_points()  # Use enum
            wrist = points[9]
            new_pos = (int(wrist.x() * screen.get_width()), int(wrist.y() * screen.get_height()))

            if len(trail) > 0:
                speed = ((new_pos[0] - trail[-1][0]) ** 2 + (new_pos[1] - trail[-1][1]) ** 2) ** 0.5
                alpha = min(int(speed * 10), 255)
                pygame.draw.circle(screen, (255, 255, 0, alpha), new_pos, 10)

            trail.append(new_pos)
            if len(trail) > max_trail_length:
                trail.pop(0)
