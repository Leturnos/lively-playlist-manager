import os
import json
import threading
from src.utils.logger import log

# Paths relative to the project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLPAPER_DIR = os.path.join(ROOT_DIR, "wallpapers")
THUMBS_DIR = os.path.join(ROOT_DIR, "thumbs")
STATIC_WALLPAPER_DIR = os.path.join(ROOT_DIR, "Static Wallpaper")
LOCKSCREEN_PATH_A = os.path.join(STATIC_WALLPAPER_DIR, "current_lockscreen_a.jpg")
LOCKSCREEN_PATH_B = os.path.join(STATIC_WALLPAPER_DIR, "current_lockscreen_b.jpg")
CURRENT_LOCKSCREEN_PATH = LOCKSCREEN_PATH_A
CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")

# Lively-specific local library paths
LIVELY_LIBRARY = os.path.join(ROOT_DIR, "Library", "SaveData", "wallpapers")
LIVELY_WPTMP = os.path.join(ROOT_DIR, "Library", "SaveData", "wptmp")

def find_lively_exe():
    """Attempts to locate Lively.exe in common installation paths."""
    # 1. Check Local AppData (Standard installer)
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    path1 = os.path.join(local_appdata, "Programs", "Lively Wallpaper", "Lively.exe")
    if os.path.exists(path1):
        return path1
        
    # 2. Check Program Files (x86)
    pf86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    path2 = os.path.join(pf86, "Lively Wallpaper", "Lively.exe")
    if os.path.exists(path2):
        return path2
        
    # 3. Check Program Files
    pf = os.environ.get("ProgramFiles", "C:\\Program Files")
    path3 = os.path.join(pf, "Lively Wallpaper", "Lively.exe")
    if os.path.exists(path3):
        return path3
        
    # Fallback to a common guess (won't work but prevents crash)
    return path1

DEFAULT_LIVELY_EXE = find_lively_exe()
AVAILABLE_MODES = ["video", "30s", "1min", "5min", "10min", "30min", "1h"]

_config_lock = threading.Lock()

def load_config():
    """Loads configuration from disk."""
    default_config = {
        "lively_path": DEFAULT_LIVELY_EXE,
        "mode": "video",
        "active_wallpapers": [],
        "rotation_order": "shuffle",
        "playlists": {},
        "current_playlist": "All Wallpapers",
        "duration_cache": {},
        "target_monitor": None,
        "sync_lockscreen": False,
        "last_played_wallpaper": None
    }
    
    with _config_lock:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Use current keys, fallback to defaults
                config = {
                    "lively_path": data.get("lively_path", default_config["lively_path"]),
                    "mode": data.get("mode", default_config["mode"]),
                    "active_wallpapers": data.get("active_wallpapers", default_config["active_wallpapers"]),
                    "rotation_order": data.get("rotation_order", default_config["rotation_order"]),
                    "playlists": data.get("playlists", default_config["playlists"]),
                    "current_playlist": data.get("current_playlist", default_config["current_playlist"]),
                    "duration_cache": data.get("duration_cache", default_config["duration_cache"]),
                    "target_monitor": data.get("target_monitor", default_config["target_monitor"]),
                    "sync_lockscreen": data.get("sync_lockscreen", default_config["sync_lockscreen"]),
                    "last_played_wallpaper": data.get("last_played_wallpaper", default_config["last_played_wallpaper"])
                }
                
                if config["mode"] not in AVAILABLE_MODES:
                    config["mode"] = "video"
                    
                return config
            except Exception as e:
                log(f"Error loading config: {e}")
                
    return default_config

def save_config(config_data):
    """Saves the current configuration to disk atomically."""
    with _config_lock:
        tmp_file = f"{CONFIG_FILE}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, CONFIG_FILE)
        except Exception as e:
            log(f"Error saving config: {e}")
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass

# Initial load
config = load_config()
