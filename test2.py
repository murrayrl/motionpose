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

chest_points = list()

def main():
    # Initialize ZED camera
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720  # Use HD1080 video mode
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
    dpg.create_viewport(title="ZED Camera Viewer", width=1280, height=720)
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

    
    with dpg.window(label="Camera Parameters"):
        dpg.add_text("Person 1", tag="person1")
        dpg.add_text("No Position", tag="coordinate1")

        dpg.add_text("Person 2", tag="person2")
        dpg.add_text("No Position", tag="coordinate2")

        dpg.add_text("Person 3", tag="person3")
        dpg.add_text("No Position", tag="coordinate3")


    
    def update_frame():
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            # Retrieve the image
            zed.retrieve_image(image, sl.VIEW.LEFT, sl.MEM.CPU, display_resolution)
            #bodies = sl.Bodies()
            zed.retrieve_bodies(bodies, body_runtime_param)

            img_bgr = image.get_data()
            
            cv_viewer.render_2D(img_bgr,image_scale, bodies.body_list, body_param.enable_tracking, body_param.body_format) # This overalys a render onto the display
            #if bodies.body_list:
                #print(bodies.body_list[0].id)
            #global chest_points
            
            '''# Loop through bodies and collect the zed keypoint[2] (assuming the body keypoint is an array of [x, y, z])
            for body in bodies.body_list:
                #print(f"{body.id} {body.tracking_state}")
                if str(body.tracking_state) == 'OK':
                    
                    if str(dpg.get_value("person1")) == "Not Tracking" or int(dpg.get_value("person1")) == int(body.id):
                        keypoint = body.keypoint[2]  # Get the 3D coordinates [x, y, z] 
                        dpg.set_value("coordinate1", keypoint)
                        dpg.set_value("person1", body.id)
                    elif str(dpg.get_value("person2")) == "Not Tracking" or int(dpg.get_value("person2")) == int(body.id):
                        keypoint = body.keypoint[2]  # Get the 3D coordinates [x, y, z] 
                        dpg.set_value("coordinate1", keypoint)
                        dpg.set_value("person1", body.id)
                    elif str(dpg.get_value("person3")) == "Not Tracking" or int(dpg.get_value("person3")) == int(body.id):
                        keypoint = body.keypoint[2]  # Get the 3D coordinates [x, y, z] 
                        dpg.set_value("coordinate1", keypoint)
                        dpg.set_value("person1", body.id)'''
            
            counter = 0
            
            
            temp_bodies = {}
            for body in bodies.body_list:
                if str(body.tracking_state) == "OK" and counter < 3:
                    keypoint = body.keypoint[2]  # Get the 3D coordinates [x, y, z] 
                    temp_bodies.update({counter: keypoint})
                    counter += 1


            tracked_bodies = temp_bodies
            try:
                dpg.set_value("coordinate1", tracked_bodies[0])
                #dpg.set_value("person1", 1)
                dpg.set_value("coordinate2", tracked_bodies[1])
                #dpg.set_value("person2", 2)
                dpg.set_value("coordinate3", tracked_bodies[2])
                #dpg.set_value("person3", body.id)
            except:
                pass

            
            print(tracked_bodies)

            

            

            # Convert to RGBA format
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            img_rgba = np.zeros((img_rgb.shape[0], img_rgb.shape[1], 4), dtype=np.float32)
            img_rgba[:, :, :3] = img_rgb / 255.0
            img_rgba[:, :, 3] = 1.0  # Alpha channel
            
            # Update texture
            dpg.set_value("camera_texture", img_rgba.ravel())

            

    dpg.show_viewport()
    
    # Main loop
    while dpg.is_dearpygui_running():
        update_frame()
        dpg.render_dearpygui_frame()

    # Cleanup
    zed.close()
    dpg.destroy_context()

if __name__ == "__main__":
    main()

def calculate_averages(coords):
    # Convert the list of coordinates to a NumPy array (if not already)
    coords_array = np.array(coords)
    
    # Calculate the averages for x, y, and z
    x_avg = np.mean(coords_array[:, 0])
    y_avg = np.mean(coords_array[:, 1])
    z_avg = np.mean(coords_array[:, 2])
    
    print(f"Averaged x: {x_avg}, y: {y_avg}, z: {z_avg}")