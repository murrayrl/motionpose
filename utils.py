import logging
import os
import sys
import tempfile

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def setup_logging():
    """Setup logging to both console and file for the packaged application"""
    # Create a log file in a writable location
    if getattr(sys, 'frozen', False):
        # If running as packaged app
        log_dir = os.path.join(os.path.expanduser("~"), ".motionpose2i", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "motionpose.log")
    else:
        # In development
        log_file = "motionpose.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    # Log startup information
    logging.info(f"Application started - Log file: {log_file}")
    logging.info(f"Running from: {os.getcwd()}")
    return log_file