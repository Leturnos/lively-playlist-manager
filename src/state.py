import threading

# Threading Events
skip_event = threading.Event()
stop_event = threading.Event()
play_specific_event = threading.Event()
play_previous_event = threading.Event()

# Global State
is_paused = False
current_video = None  # Current playing filename
next_video_request = None  # Path for "Play Now" feature
is_window_open = False
playlist_needs_reload = False
is_going_back = False
history = []  # List of video paths
hotkey_thread_id = None
current_active_time = 0.0
current_effective_limit = 0.0

# Locks
thumbs_lock = threading.Lock()
thumbs_ready = {}
