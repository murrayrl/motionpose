import pygame

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pygame Test Window")

# Colors
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)

# Circle properties
circle_x, circle_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
circle_radius = 30
speed = 5

# Main loop
running = True
while running:
    screen.fill(WHITE)  # Clear screen

    # Draw circle
    pygame.draw.circle(screen, BLUE, (circle_x, circle_y), circle_radius)

    pygame.display.flip()  # Update the display

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:  # Close window
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:  # Exit on ESC key
                running = False
            elif event.key == pygame.K_LEFT:  # Move left
                circle_x -= speed
            elif event.key == pygame.K_RIGHT:  # Move right
                circle_x += speed
            elif event.key == pygame.K_UP:  # Move up
                circle_y -= speed
            elif event.key == pygame.K_DOWN:  # Move down
                circle_y += speed

pygame.quit()
