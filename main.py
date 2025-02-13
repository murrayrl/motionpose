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
    display_resolution = sl.Resolution(min(camera_info.camera_configuration.resolution.width, 1280), min(camera_info.camera_configuration.resolution.height, 720))
    image_scale = [display_resolution.width / camera_info.camera_configuration.resolution.width
                 , display_resolution.height / camera_info.camera_configuration.resolution.height]


    # Create image objects
    bodies = sl.Bodies()
    tracked_bodies = {}

    image = sl.Mat()
    key_wait = 10 
    skeleton_file_data = {}
    
    # Initialize Dear PyGUI
    dpg.create_context()
    dpg.create_viewport(title="ZED Camera Viewer", width=1920, height=1080)
    dpg.setup_dearpygui()

    # Create texture registry
    with dpg.texture_registry():
        # Empty texture
        dpg.add_raw_texture(
            width=1280,
            height=720,
            default_value=np.zeros((720, 1280, 4), dtype=np.float32),
            format=dpg.mvFormat_Float_rgba,
            tag="camera_texture"
        )

    # Create window
    with dpg.window(label="ZED Camera Feed", width=1280, height=720):
        dpg.add_image("camera_texture")

    
    with dpg.window(label="Camera Parameters", width=300):
        dpg.add_text("Person 1", tag="person1")
        dpg.add_text("No Position", tag="coordinate1")

        dpg.add_text("Person 2", tag="person2")
        dpg.add_text("No Position", tag="coordinate2")

        dpg.add_text("Person 3", tag="person3")
        dpg.add_text("No Position", tag="coordinate3")

        dpg.add_text("Person 4", tag="person4")
        dpg.add_text("No Position", tag="coordinate4")

        dpg.add_text("Person 5", tag="person5")
        dpg.add_text("No Position", tag="coordinate5")


    with dpg.window(label="Dynamic Art", width=1920, height=1080):
        # Create a drawlist widget that serves as our canvas.
        # We assign it a tag ("drawing") so we can reference it later.
        with dpg.drawlist(width=1920, height=1080, tag="canvas"):
            # Initially, you can draw static shapes here if desired.
            pass
    
    start_time = time.time()

    # def update_drawing(tracked_bodies):
    #     """Update the drawing canvas with new shapes based on the current time."""
    #     # Calculate elapsed time.
    #     dpg.delete_item("canvas", children_only=True)
        
    #     if len(tracked_bodies):
    #         body = tracked_bodies[0]
    #         for joint in range(33):
    #             keypoint = body.keypoint_2d[joint]
    #             #print(keypoint[0])
    #             dpg.draw_circle(center=(keypoint[0], keypoint[1]),
    #                         radius=50,
    #                         color=[255, 0, 0],
    #                         fill=[255, 0, 0, 255],
    #                         thickness=2,
    #                         parent="canvas")
    #def update_drawing(tracked_bodies):
        



        



    def update_frame():
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_image(image, sl.VIEW.LEFT, sl.MEM.CPU, display_resolution) # Retrieve the image
            zed.retrieve_bodies(bodies, body_runtime_param)

            img_bgr = image.get_data()
            
            cv_viewer.render_2D(img_bgr,image_scale, bodies.body_list, body_param.enable_tracking, body_param.body_format) # This overalys a render onto the display
            #if bodies.body_list:
                #print(bodies.body_list[0].id)
            #global chest_points
            
            # Loop through bodies and collect the zed keypoint[2] (assuming the body keypoint is an array of [x, y, z])
        
            counter = 0   
            tracked_bodies = {}        
            for body in bodies.body_list:
                if str(body.tracking_state) == "OK" and counter < 5:
                    #keypoint = body.keypoint_2d[15]  # Get the 3D coordinates [x, y, z] 
                    tracked_bodies.update({counter: body})
                    counter += 1

            effects.day_to_night(tracked_bodies) # calls the effect from effects.py

            try:
                dpg.set_value("coordinate1", tracked_bodies[0].keypoint_2d[2])
                dpg.set_value("coordinate2", tracked_bodies[1].keypoint_2d[2])
                dpg.set_value("coordinate3", tracked_bodies[2].keypoint_2d[2])
                dpg.set_value("coordinate4", tracked_bodies[3].keypoint_2d[2])
                dpg.set_value("coordinate5", tracked_bodies[4].keypoint_2d[2])

            except:
                pass

            #print(tracked_bodies)
            # Convert to RGBA format
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            img_rgba = np.zeros((img_rgb.shape[0], img_rgb.shape[1], 4), dtype=np.float32)
            img_rgba[:, :, :3] = img_rgb / 255.0
            img_rgba[:, :, 3] = 1.0  # Alpha channel
            
            # Update texture
            dpg.set_value("camera_texture", img_rgba.ravel())

    dpg.show_viewport()
    
    # Main loop
    while dpg.is_dearpygui_running(): # while program is running
        update_frame()
        
        dpg.render_dearpygui_frame()

    # Cleanup
    zed.close()
    dpg.destroy_context()

if __name__ == "__main__":
    main()