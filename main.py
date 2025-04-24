import dearpygui.dearpygui as dpg
import pyzed.sl as sl
import cv2
import numpy as np
import ogl_viewer.viewer as gl
import cv_viewer.tracking_viewer as cv_viewer
import effects
import os
import shutil
import webbrowser
import sys
import logging
from utils import setup_logging, resource_path

def open_github_homepage(): # may want to create a pop up that says "you are opening a link outside of the program, do you want to continue?"
    webbrowser.open('https://github.com/murrayrl/motionpose/tree/ZED')  # Go to ZED github page
def open_github_wiki():
    webbrowser.open('https://github.com/murrayrl/motionpose/wiki/ZED-2i-Development')  # Go to wiki



class ZEDCamera:
    """Handles ZED camera initialization, configuration and operations."""
    
    def __init__(self):
        self.camera = sl.Camera()
        self.image = sl.Mat()
        self.bodies = sl.Bodies()
        self.display_resolution = None
        self.image_scale = None
        
    def initialize(self):
        """Initialize and configure the ZED camera."""
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD1080
        init_params.coordinate_units = sl.UNIT.METER
        init_params.depth_mode = sl.DEPTH_MODE.ULTRA
        init_params.coordinate_system = sl.COORDINATE_SYSTEM.LEFT_HANDED_Y_UP
        
        # Open the camera
        err = self.camera.open(init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            logging.error(f"Error opening camera: {err}")
            return False
            
        # Enable positional tracking
        positional_tracking_parameters = sl.PositionalTrackingParameters()
        # If the camera is static, uncomment the following line for better performance
        # positional_tracking_parameters.set_as_static = True
        self.camera.enable_positional_tracking(positional_tracking_parameters)
        
        # Configure body tracking
        body_param = sl.BodyTrackingParameters()
        body_param.enable_tracking = True
        body_param.enable_body_fitting = True
        body_param.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST
        body_param.body_format = sl.BODY_FORMAT.BODY_34
        
        # Enable body tracking
        self.camera.enable_body_tracking(body_param)
        
        # Store body parameters for later use
        self.body_param = body_param
        self.body_runtime_param = sl.BodyTrackingRuntimeParameters()
        self.body_runtime_param.detection_confidence_threshold = 40
        
        # Get camera information and set display resolution
        camera_info = self.camera.get_camera_information()
        self.display_resolution = sl.Resolution(
            min(camera_info.camera_configuration.resolution.width, 1920),
            min(camera_info.camera_configuration.resolution.height, 1080)
        )
        
        self.image_scale = [
            self.display_resolution.width / camera_info.camera_configuration.resolution.width,
            self.display_resolution.height / camera_info.camera_configuration.resolution.height
        ]
        
        return True
        
    def grab_frame(self):
        """Grab a new frame from the camera."""
        return self.camera.grab() == sl.ERROR_CODE.SUCCESS
        
    def get_image_and_bodies(self):
        """Retrieve the current image and detected bodies."""
        self.camera.retrieve_image(self.image, sl.VIEW.LEFT, sl.MEM.CPU, self.display_resolution)
        self.camera.retrieve_bodies(self.bodies, self.body_runtime_param)
        
        img_bgr = self.image.get_data()
        cv_viewer.render_2D(
            img_bgr, 
            self.image_scale, 
            self.bodies.body_list, 
            self.body_param.enable_tracking, 
            self.body_param.body_format
        )
        
        # Process tracked bodies
        tracked_bodies = {}
        counter = 0
        for body in self.bodies.body_list:
            if str(body.tracking_state) == "OK" and counter < 5:
                tracked_bodies.update({counter: body})
                counter += 1
                
        return img_bgr, tracked_bodies
        
    def close(self):
        """Close the camera properly."""
        self.camera.close()


'''----------------------------------------------- End of ZED Camera Class ----------------------------------------------------------------'''


class MotionPoseUI:
    """Handles the DearPyGUI interface setup and management."""
    
    def __init__(self, width=1920, height=1080):
        self.width = width
        self.height = height
        self.zed_window_tag = dpg.generate_uuid()
        self.effect_window_tag = dpg.generate_uuid()
        
    def initialize(self):
        """Initialize the UI components."""
        # Add resource path helper function at the beginning of your file
        def resource_path(relative_path):
            """Get absolute path to resource, works for dev and for PyInstaller"""
            try:
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)
        
        # Use resource_path for source file
        source_layout = resource_path("custom_layout.ini")
        
        # For user_custom_layout.ini, use a writable location (not inside the package)
        user_dir = os.path.expanduser("~/.motionpose2i")
        os.makedirs(user_dir, exist_ok=True)
        user_layout = os.path.join(user_dir, "user_custom_layout.ini")
        
        # Check for custom layout file
        if not os.path.exists(user_layout):
            shutil.copy(source_layout, user_layout)
        
        # Configure the application
        dpg.configure_app(
            load_init_file=user_layout,
            docking=True,
            docking_space=True
        )
    
        # Create viewport
        dpg.create_viewport(
            title="Motionpose 2i",
            width=self.width,
            height=self.height
        )
    
        # Setup texture registry
        self._setup_texture_registry()
    
        # Create windows
        self._setup_menu_bar()
        self._create_camera_window()
        self._create_effect_window()
    
        # Setup and show
        dpg.setup_dearpygui()
        dpg.show_viewport()
        
    def _setup_menu_bar(self):
        with dpg.viewport_menu_bar():
            with dpg.menu(label="File"):
                ...
                
            with dpg.menu(label="Edit"):
                pass

            with dpg.menu(label="View"):
                pass

            with dpg.menu(label="Help"):
                dpg.add_menu_item(label="Quick Help", callback=open_github_homepage) # opens ZED github page
                dpg.add_menu_item(label="Diagnostics") # idk what this will do
                dpg.add_menu_item(label="About Motionpose", callback=open_github_wiki) # opens ZED wiki page
            

    def _setup_texture_registry(self):
        """Setup texture registry for camera image."""
        with dpg.texture_registry():
            dpg.add_raw_texture(
                width=self.width,
                height=self.height,
                default_value=np.zeros((self.height, self.width, 4), dtype=np.float32),
                format=dpg.mvFormat_Float_rgba,
                tag="camera_texture"
            )
            
    def _create_camera_window(self):
        """Create the camera display window."""
        with dpg.window(label="ZEDCamera", width=self.width, height=self.height, tag=self.zed_window_tag):
            dpg.add_image("camera_texture")
        

    def _create_effect_window(self):
        """Create the effect controls window."""
        with dpg.window(label="EffectDisplay", width=self.width, height=self.height, tag=self.effect_window_tag):
            with dpg.group(horizontal=True, tag="menu_bar"):
                dpg.add_combo(
                    effects.effect_list,
                    tag="effect_combo",
                    width=200,
                    callback=self.update_ui_for_effect,
                    default_value="Select an effect"
                )
                
            with dpg.drawlist(width=self.width, height=self.height, tag="canvas"):
                pass
                
            with dpg.group(tag="dynamic_ui"):
                pass
                
    def update_ui_for_effect(self):
        """Update UI elements based on selected effect."""
        if dpg.does_item_exist("effect_control"):
            dpg.delete_item("effect_control")
            
        with dpg.group(parent="menu_bar", tag="effect_control", horizontal=True):
            if dpg.get_value("effect_combo") == "Multitrack Music":
                
                dpg.add_combo(
                    effects.song_list,
                    tag="song_combo",
                    width=350,
                    default_value="Select a song"
                )
                dpg.add_button(
                    label="Start",
                    callback=self.update_song_for_effect
                )
                dpg.add_button(
                    label="Stop",
                    callback=effects.sound_stop
                )
            if dpg.get_value("effect_combo") == "3d Volume Controller":
                dpg.add_combo(
                    tag="song_combo",
                    width=350,
                    default_value="Billy Joel - Movin' Out (Anthony's Song)"
                )
                dpg.add_button(
                    label="Start",
                    callback=self.update_song_for_effect
                )
                dpg.add_button(
                    label="Stop",
                    callback=effects.sound_stop
                )
                
    def update_song_for_effect(self):
        """Start playing selected song."""
        if dpg.does_item_exist("song_combo"):
            effects.sound_start(dpg.get_value("song_combo"))
            
    def update_frame_display(self, img_rgba):
        """Update the displayed camera frame."""
        dpg.set_value("camera_texture", img_rgba.ravel())
        
    def is_running(self):
        """Check if the UI is still running."""
        return dpg.is_dearpygui_running()
        
    def render_frame(self):
        """Render a single frame."""
        dpg.render_dearpygui_frame()
        
    def cleanup(self):
        """Clean up resources."""
        dpg.destroy_context()

'''----------------------------------------------- End of DearPyGui Class ----------------------------------------------------------------'''

def main():
    # Create DearPyGUI context
    dpg.create_context()
    log_file = setup_logging()
    logging.info("Starting import of custom modules")
    try:
        import cv_viewer.tracking_viewer as cv_viewer
        logging.info("Successfully imported cv_viewer")
    except Exception as e:
        logging.error(f"Error importing cv_viewer: {e}")

    try:
        import ogl_viewer.viewer as gl
        logging.info("Successfully imported ogl_viewer")
    except Exception as e:
        logging.error(f"Error importing ogl_viewer: {e}")


    # Initialize camera
    zed_camera = ZEDCamera()
    if not zed_camera.initialize():
        dpg.destroy_context()
        return
        
    # Initialize UI
    ui = MotionPoseUI()
    ui.initialize()
    
    # Main loop
    while ui.is_running():
        if zed_camera.grab_frame():
            # Get image and tracked bodies
            img_bgr, tracked_bodies = zed_camera.get_image_and_bodies()
            
            # Process effects based on selection
            selected_effect = dpg.get_value("effect_combo")
            effects.call_effect(tracked_bodies, selected_effect)
            
            # Convert image for display
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            img_rgba = np.zeros((img_rgb.shape[0], img_rgb.shape[1], 4), dtype=np.float32)
            img_rgba[:, :, :3] = img_rgb / 255.0
            img_rgba[:, :, 3] = 1.0  # Alpha channel
            
            # Update display
            ui.update_frame_display(img_rgba)
            
        ui.render_frame()
    
    # Cleanup
    zed_camera.close()
    ui.cleanup()

    logging.info("Application Closing")


if __name__ == "__main__":
    main()