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
        dpg.add_text("Fart")
        dpg.add_button(label="Save")
        dpg.add_input_text(label="string", default_value="Quick brown fox")
        dpg.add_slider_float(label="float", default_value=0.273, max_value=1)

    def update_frame():
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            # Retrieve the image
            zed.retrieve_image(image, sl.VIEW.LEFT, sl.MEM.CPU, display_resolution)
            zed.retrieve_bodies(bodies, body_runtime_param)
            img_bgr = image.get_data()
            cv_viewer.render_2D(img_bgr,image_scale, bodies.body_list, body_param.enable_tracking, body_param.body_format) # This overalys a render onto the display
            
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