import dearpygui.dearpygui as dpg
import pyzed.sl as sl
import cv2
import numpy as np
import cv2
import sys
import pyzed.sl as sl
import ogl_viewer.viewer as gl
import time
import cv_viewer.tracking_viewer as cv_viewer
import numpy as np
import argparse
import math
import random 
import effects
import os
import shutil

dpg.create_context()





def main():
    # Initialize ZED camera
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD1080  # Use HD1080 video mode
    init_params.coordinate_units = sl.UNIT.METER          # Set coordinate units
    init_params.depth_mode = sl.DEPTH_MODE.ULTRA
    init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP

    # Open the camera
    err = zed.open(init_params)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Error opening camera: {err}")
        return

    # Enable Positional tracking (mandatory for object detection)
    positional_tracking_parameters = sl.PositionalTrackingParameters()
    # If the camera is static, uncomment the following line to have better performances
    # positional_tracking_parameters.set_as_static = True
    zed.enable_positional_tracking(positional_tracking_parameters)
    
    body_param = sl.BodyTrackingParameters()
    body_param.enable_tracking = True                # Track people across images flow
    body_param.enable_body_fitting = True            # Smooth skeleton move
    body_param.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST 
    body_param.body_format = sl.BODY_FORMAT.BODY_34  # Choose the BODY_FORMAT you wish to use

    # Enable Object Detection module
    zed.enable_body_tracking(body_param)

    body_runtime_param = sl.BodyTrackingRuntimeParameters()
    body_runtime_param.detection_confidence_threshold = 40

    # Get ZED camera information
    camera_info = zed.get_camera_information()
    # 2D viewer utilities
    display_resolution = sl.Resolution(min(camera_info.camera_configuration.resolution.width, 1920), min(camera_info.camera_configuration.resolution.height, 1080))
    image_scale = [display_resolution.width / camera_info.camera_configuration.resolution.width
                 , display_resolution.height / camera_info.camera_configuration.resolution.height]

    # Create image objects
    bodies = sl.Bodies()
    image = sl.Mat()

    #create Queue for music player


    
    if not os.path.exists("user_custom_layout.ini"):
        shutil.copy("custom_layout.ini", "user_custom_layout.ini")

    # Initialize Dear PyGUI
    dpg.configure_app(load_init_file="user_custom_layout.ini", docking=True, docking_space=True) # must be called before create_viewport
    dpg.create_viewport(title="Motionpose 2i", width=1920, height=1080)
    
    ZEDCamera = dpg.generate_uuid()
    EffectDisplay = dpg.generate_uuid()

    # Create texture registry
    with dpg.texture_registry():
        # Empty texture
        dpg.add_raw_texture(
            width=1920,
            height=1080,
            default_value=np.zeros((1080, 1920, 4), dtype=np.float32),
            format=dpg.mvFormat_Float_rgba,
            tag="camera_texture"
        )

    # Create window
    with dpg.window(label="ZEDCamera", width=1920, height=1080, tag=ZEDCamera):
        dpg.add_image("camera_texture")
        """Dynamically update UI elements based on the selected effect."""
        

    # Create EffectDisplay window before calling update_ui_for_effect
    with dpg.window(label="EffectDisplay", width=1920, height=1080, tag=EffectDisplay):
        with dpg.group(horizontal=True, tag="menu_bar"):

            def update_song_for_effect(): # updates when effect is selected
                if dpg.does_item_exist("song_combo"):
                    effects.sound_start(dpg.get_value("song_combo"))
            
            def update_ui_for_effect(): # updates when effect is selected
                if dpg.does_item_exist("effect_control"):
                    dpg.delete_item("effect_control") # deletes group to be recreated below

                with dpg.group(parent="menu_bar", tag="effect_control", horizontal=True):
                    #dpg.add_checkbox(label="Effect Checkbox", default_value=True)
                    if dpg.get_value("effect_combo") == "Sound": # check if sound is created
                        dpg.add_combo(
                            effects.song_list,  
                            tag="song_combo",
                            width=300,
                            #callback=update_ui_for_effect,  # Delayed binding
                            default_value="Select a song"
                        )
                        dpg.add_button(
                            label="Start",
                            callback=update_song_for_effect,
                            #user_data=dpg.get_value("song_combo")
                        )
                        dpg.add_button(
                            label="Stop",
                            callback=effects.sound_stop 
                        )

            dpg.add_combo(
                effects.effect_list,  
                tag="effect_combo",
                width=300,
                callback=update_ui_for_effect,  # Delayed binding
                default_value="Select an effect"
            )
            
                        #dpg.add_checkbox(label="Effect Checkbox", default_value=True)
            #dpg.add_checkbox(label="Effect Checkbox 2", default_value=False)

        with dpg.drawlist(width=1920, height=1080, tag="canvas"):
            pass

        with dpg.group(tag="dynamic_ui"):
            pass
    
    
    dpg.setup_dearpygui()
    dpg.show_viewport()
    #dpg.start_dearpygui()
    #dpg.show_debug()

    

    
    def update_frame():
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_image(image, sl.VIEW.LEFT, sl.MEM.CPU, display_resolution) # Retrieve the image
            zed.retrieve_bodies(bodies, body_runtime_param)

            img_bgr = image.get_data()
            
            cv_viewer.render_2D(img_bgr,image_scale, bodies.body_list, body_param.enable_tracking, body_param.body_format) # This overalys a render onto the display
            
            # Loop through bodies and collect the zed keypoint[2] (assuming the body keypoint is an array of [x, y, z])
        
            counter = 0   
            tracked_bodies = {}        
            for body in bodies.body_list:
                if str(body.tracking_state) == "OK" and counter < 5:
                    #keypoint = body.keypoint_2d[15]  # Get the 3D coordinates [x, y, z] 
                    tracked_bodies.update({counter: body})
                    counter += 1

            selected_effect = dpg.get_value("effect_combo")          
            

            #print(dpg.get_value("song_combo"))

            effects.call_effect(tracked_bodies, selected_effect) # calls the effect from effects.py

            # Convert to RGBA format
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            img_rgba = np.zeros((img_rgb.shape[0], img_rgb.shape[1], 4), dtype=np.float32)
            img_rgba[:, :, :3] = img_rgb / 255.0
            img_rgba[:, :, 3] = 1.0  # Alpha channel
            
            # Update texture
            dpg.set_value("camera_texture", img_rgba.ravel())

    # Main loop
    while dpg.is_dearpygui_running(): # while program is running
        update_frame()
        dpg.render_dearpygui_frame()

    # Cleanup
    zed.close()
    dpg.destroy_context()


if __name__ == "__main__":
    main()



