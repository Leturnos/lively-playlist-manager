import threading

# Threading Events
skip_event = threading.Event()
stop_event = threading.Event()
play_specific_event = threading.Event()

# Global State
is_paused = False
current_video = None  # Current playing filename
next_video_request = None  # Path for "Play Now" feature
is_window_open = False

# Locks
thumbs_lock = threading.Lock()
thumbs_ready = {}
