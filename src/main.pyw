import os
import sys
import threading

# Add the project root to sys.path to allow absolute imports
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.playlist import run_rotation_engine
from src.utils.thumbnails import background_thumbnail_generator
from src.utils.hotkeys import start_hotkey_listener
from src.ui.tray import start_tray

def main():
    """Application entry point. Initializes threads for rotation, thumbnails, hotkeys, and the UI tray."""
    # Start the rotation engine in the background
    rotation_thread = threading.Thread(target=run_rotation_engine, daemon=True)
    rotation_thread.start()
    
    # Start the thumbnail generator in the background
    thumb_thread = threading.Thread(target=background_thumbnail_generator, daemon=True)
    thumb_thread.start()
    
    # Start global hotkeys listener in the background
    hotkey_thread = threading.Thread(target=start_hotkey_listener, daemon=True)
    hotkey_thread.start()
    
    # Start the system tray (this is a blocking call on the main thread)
    start_tray()
    
    # Once the tray icon is stopped, the application will exit
    sys.exit(0)

if __name__ == "__main__":
    main()
