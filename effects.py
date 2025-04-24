import dearpygui.dearpygui as dpg
import math
import random
import time
from pygame import mixer
import numpy as np
from utils import resource_path
import logging
import os


effect_list = ("Day to Night", "Multitrack Music", "3d Volume Controller", "Day to Night 3d")

songs = [ # includes name of song, along with the tracks that are apart of it
    {
        "name": "Jessica Childress - Slow Down",
        "tracks": ["music/sd_bass.wav", "music/sd_drums.wav", "music/sd_guitar.wav", "music/sd_keyboard.wav", "music/sd_vocals.wav"]
    },
    {
        "name": "Billy Joel - Movin' Out (Anthony's Song)",
        "tracks": ["music/billymusic.mp3", "music/billyvocal.mp3"]
    },
    {
        "name": "Chicago_Someday",
        "tracks": ["music/Piano & Horns only.mp3", "music/No Horns or rhythm guitars - Rbert Lamm Peter Cetera.mp3","music/Guitars, Horns.mp3"]
    }
]
song_list = tuple(song["name"] for song in songs) # grabs song list from the names inside songs


def call_effect(tracked_bodies, selected_effect):
    '''Effect handler'''
    if selected_effect == "Day to Night":
        day_to_night(tracked_bodies)
        
    elif selected_effect == "Multitrack Music":
        sound(tracked_bodies)

    elif selected_effect == "3d Volume Controller":
        sound_3d(tracked_bodies)

    # elif selected_effect == "Day to Night 3d":
    #     day_to_night_3d(tracked_bodies)
        

def sound_3d(tracked_bodies):
    '''Handles muting/unmuting audio for sound effect'''
    #floating_circles(tracked_bodies)
    
    if mixer.get_init() is None:  # early return if mixer isn't running
        return
    
    num_bodies = len(tracked_bodies)

    if num_bodies > 0:

        head_y = tracked_bodies[0].keypoint[26][1] # head
        pelvis_y = tracked_bodies[0].keypoint[0][1] 

        hand_y_right = tracked_bodies[0].keypoint[15][1] # right
        hand_y_left = tracked_bodies[0].keypoint[8][1] # left

        body_height = abs(head_y - pelvis_y)
        hand_height_right = hand_y_right - pelvis_y
        hand_height_left = hand_y_left - pelvis_y


        normalized_height_right = hand_height_right / body_height
        normalized_height_left = hand_height_left / body_height

        normalized_height_right = np.clip(normalized_height_right, 0.0, 1.0)
        normalized_height_left = np.clip(normalized_height_left, 0.0, 1.0)

        
        right_vol = np.clip(normalized_height_right, 0.0, 1.0) # clamp value to not go over
        left_vol = np.clip(normalized_height_left, 0.0, 1.0) # clamp value to not go over

        mixer.Channel(0).set_volume(right_vol)
        mixer.Channel(1).set_volume(left_vol)

        progress_bar(left_vol, right_vol)
    

def day_to_night_3d(tracked_bodies):
    ...

def floating_circles(tracked_bodies): # art effect that goes with sound
    """
    Creates an animation of circles smoothly and slowly floating up from the bottom 
    of the screen and disappearing when they reach the top. The color of the circles 
    depends on the number of people detected in the frame.
    """
    width = dpg.get_viewport_width()
    height = dpg.get_viewport_height()
    
    dpg.delete_item("canvas", children_only=True)
    
    # Draw a basic background
    dpg.draw_rectangle(
        (0, 0),
        (width, height),
        fill=(10, 10, 20),  # Dark background
        parent="canvas"
    )
    
    # Count the number of people in frame
    num_people = len(tracked_bodies)
    
    # No circles to create if no people are in frame
    if num_people == 0:
        return
    
    # Define circle color based on the number of people in the frame
    if num_people >= 0:
        color = (255, 0, 0, 200)  # Red for 1 person
    elif num_people >= 1:
        color = (0, 0, 255, 200)  # Blue for 2 people
    elif num_people >= 2:
        color = (0, 255, 0, 200)  # Green for 3 people
    else:
        # For 4+ people, use a random pastel color
        r = random.randint(100, 255)
        g = random.randint(100, 255)
        b = random.randint(100, 255)
        color = (r, g, b, 200)  # Pastel color for more than 3 people
    
    # Use current time for smooth animation
    current_time = time.time()
    
    # Store circle data in a global variable to maintain consistency between frames
    global circle_data
    
    # Initialize circle data if it doesn't exist
    if 'circle_data' not in globals() or not isinstance(circle_data, list):
        circle_data = []
        
        # Generate initial circle data based on the number of people
        num_circles = num_people * 20  # More circles for more people
        
        for i in range(num_circles):
            # Random initial position
            x = random.uniform(0, width)
            # Start at different heights below and within the screen
            y = random.uniform(height * 0.5, height + 200)
            
            # Random size
            size = random.uniform(8, 25)
            
            # Use the calculated color for the circles
            # Random but slow speed - much slower than before
            speed = random.uniform(5, 15)  # pixels per second
            
            # Add to circle data
            circle_data.append({
                'x': x,
                'y': y,
                'size': size,
                'color': color,
                'speed': speed,
                'last_update': current_time
            })
    
    # Update circle positions based on elapsed time
    new_circle_data = []
    
    for circle in circle_data:
        # Calculate time delta for smooth movement
        delta_time = current_time - circle['last_update']
        
        # Update position based on speed and time elapsed
        new_y = circle['y'] - (circle['speed'] * delta_time)
        
        # Reset circles that have moved off the top of the screen
        if new_y < -50:
            # Reset to bottom
            new_y = height + random.uniform(0, 100)
            # Randomize x position for variety
            new_x = random.uniform(0, width)
            # Update the circle data
            circle['x'] = new_x
        else:
            new_x = circle['x']
        
        # Only keep circles that are visible or will be soon
        if new_y < height + 300:
            # Update circle data
            circle['x'] = new_x
            circle['y'] = new_y
            circle['last_update'] = current_time
            new_circle_data.append(circle)
            
            # Draw the circle if it's on screen
            if -50 <= new_y <= height + 50:
                dpg.draw_circle(
                    center=(new_x, new_y),
                    radius=circle['size'],
                    fill=circle['color'],
                    color=circle['color'],
                    parent="canvas"
                )
    
    # Update the global circle data
    circle_data = new_circle_data

def progress_bar(left_z, right_z):
    
    # Unpack the progress values
    progress1, progress2 = left_z, right_z
    
    # Ensure values are within range
    # progress1 = max(0.0, min(1.0, progress1))
    # progress2 = max(0.0, min(1.0, progress2))
    
    # Get canvas size
    canvas_width = dpg.get_viewport_width()
    canvas_height = dpg.get_viewport_height()
    
    #dpg.delete_item("canvas", children_only=True)
    
    # Calculate rectangle dimensions
    rect_width = canvas_width / 2.0
    
    # Draw the first rectangle (left half)
    rect1_height = progress1 * canvas_height
    rect1_start_y = canvas_height - rect1_height
    
    # Draw the second rectangle (right half)
    rect2_height = progress2 * canvas_height
    rect2_start_y = canvas_height - rect2_height
    
    # Delete previous rectangles if they exist
    if dpg.does_item_exist("canvas"):
        dpg.delete_item("canvas", children_only=True)

    
    # Draw new rectangles
    
    # First rectangle (left side)
    dpg.draw_rectangle(
        pmin=[0, rect1_start_y],
        pmax=[rect_width, canvas_height],
        color=[0, 255, 0, 255],
        fill=[0, 200, 0, 200],
        parent="canvas"
    )
    
    # Second rectangle (right side)
    dpg.draw_rectangle(
        pmin=[rect_width, rect2_start_y],
        pmax=[canvas_width, canvas_height],
        color=[0, 0, 255, 255],
        fill=[0, 0, 200, 200],
        parent="canvas"
    )

def sound(tracked_bodies):
    '''Handles muting/unmuting audio for sound effect'''
    floating_circles(tracked_bodies)

    if mixer.get_init() is None:  # early return if mixer isn't running
        return
    
    mixer.Channel(0).set_volume(1.0)

    num_bodies = len(tracked_bodies)
    
    # Set volumes for channels 1-4 based on number of tracked bodies
    for channel_num in range(1, 5):
        volume = 1.0 if num_bodies >= channel_num else 0.0
        mixer.Channel(channel_num).set_volume(volume)

def sound_start(song): # start music effect
    '''Initializes the pygame mixer and also starts music based on song selection'''
    mixer.pre_init(44100, -16, 2, 512)
    mixer.init() # turn on music system
    
    # Logging for debugging
    logging.info(f"Starting sound: {song}")
    
    # find song from callback
    try:
        tracks = next(item for item in songs if item["name"] == song)["tracks"]
        logging.info(f"Found tracks: {tracks}")
        
        for track in tracks:
            # Use resource_path for each audio file
            track_path = resource_path(track)
            logging.info(f"Loading track: {track_path}")
            logging.info(f"File exists: {os.path.exists(track_path)}")
            
            mixer.Channel(tracks.index(track)).play(mixer.Sound(track_path)) # start playing drums
            mixer.Channel(tracks.index(track)).pause() # are you fucking kidding me why does this work
            
        # this is so stupid it shouldnt work
        # we did this because before the audio had a delay between them.
        for i in range(len(tracks)):
            mixer.Channel(i).unpause()
            mixer.Channel(i).set_volume(0.0) # mute to begin
            
        logging.info("Audio playback started successfully")
    except Exception as e:
        logging.error(f"Error playing audio: {e}")
        pass

    


def sound_stop(): # clean up function music
    if mixer.get_init() is not None:
        mixer.stop() # stop all channels of music
        mixer.quit() # turns off music system
    


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
