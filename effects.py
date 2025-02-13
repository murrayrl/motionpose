import dearpygui.dearpygui as dpg
import math
import random 

def day_to_night(tracked_bodies):
        width = dpg.get_viewport_width()
        height = dpg.get_viewport_height()
        dpg.delete_item("canvas", children_only=True)
        
        # Fixed star positions as percentage of screen width/height
        star_positions = [
            (0.1, 0.1),   (0.2, 0.15),  (0.35, 0.05),
            (0.45, 0.2),  (0.5, 0.1),   (0.65, 0.15),
            (0.8, 0.05),  (0.9, 0.2),   (0.15, 0.3),
            (0.3, 0.25),  (0.4, 0.35),  (0.55, 0.3),
            (0.7, 0.25),  (0.85, 0.35), (0.05, 0.45),
            (0.25, 0.4),  (0.45, 0.45), (0.6, 0.4),
            (0.75, 0.45), (0.95, 0.4),  (0.1, 0.55),
            (0.3, 0.5),   (0.5, 0.55),  (0.7, 0.5),
            (0.9, 0.55),  (0.2, 0.6),   (0.4, 0.6),
            (0.6, 0.6),   (0.8, 0.6),   (0.15, 0.45)
        ]
        
        if len(tracked_bodies):
            head = tracked_bodies[0].keypoint_2d[26]
            head_x = head[0]
            time_factor = head_x / width
            
            # Create sky gradient based on position
            if time_factor < 0.25:  # Night
                sky_color = (0, 0, 50)
                accent_color = (255, 255, 255)  # Stars
                field_color = (0, 20, 0)  # Dark grass
            elif time_factor < 0.5:  # Sunrise
                sky_color = (255, 182, 193)
                accent_color = (255, 165, 0)    # Sun
                field_color = (34, 139, 34)     # Forest green with morning dew
            elif time_factor < 0.75:  # Day
                sky_color = (135, 206, 235)
                accent_color = (255, 255, 0)    # Sun
                field_color = (86, 125, 70)     # Bright grass
            else:  # Sunset
                sky_color = (255, 99, 71)
                accent_color = (255, 140, 0)    # Sun
                field_color = (76, 70, 50)      # Evening grass
            
            # Draw background
            dpg.draw_rectangle(
                (0, 0),
                (width, height),
                fill=sky_color,
                parent="canvas"
            )
            
            # Draw field with gentle waves
            field_start_y = height * 0.7  # Start field at 70% of screen height
            wave_points = []
            num_points = 20
            
            # Create wavy field effect
            for i in range(num_points + 1):
                x = (width / num_points) * i
                # Add subtle wave effect
                wave_offset = math.sin(i * 0.5 + time_factor * 3.14159) * 10
                y = field_start_y + wave_offset
                wave_points.append((x, y))
            
            # Add bottom corners to complete the field polygon
            wave_points.append((width, height))
            wave_points.append((0, height))
            
            # Draw the field
            dpg.draw_polygon(
                wave_points,
                fill=field_color,
                parent="canvas"
            )
            
            # Calculate arc position for celestial object
            angle = time_factor * 3.14159
            arc_height = height * 0.6
            arc_center_y = height * 0.8
            
            celestial_x = head_x
            celestial_y = arc_center_y - (math.sin(angle) * arc_height)
            
            size_factor = math.sin(angle)
            base_radius = 40
            celestial_radius = base_radius * (0.5 + size_factor * 0.5)
            
            # Draw celestial object with glow
            dpg.draw_circle(
                center=(celestial_x, celestial_y),
                radius=celestial_radius,
                fill=accent_color,
                color=accent_color,
                parent="canvas"
            )
            
            # Glow effect
            glow_radius = celestial_radius * 1.5
            glow_alpha = int(size_factor * 100)
            glow_color = (*accent_color, glow_alpha)
            dpg.draw_circle(
                center=(celestial_x, celestial_y),
                radius=glow_radius,
                fill=(*accent_color, glow_alpha),
                color=glow_color,
                parent="canvas"
            )
            
            # If it's night, draw fixed stars
            if time_factor < 0.25:
                for pos_x, pos_y in star_positions:
                    # Convert percentage positions to actual screen coordinates
                    star_x = width * pos_x
                    star_y = height * pos_y
                    
                    dpg.draw_circle(
                        center=(star_x, star_y),
                        radius=1.5,
                        fill=(255, 255, 255),
                        color=(255, 255, 255),
                        parent="canvas"
                    )