import os
import json
from src.utils.logger import log

# Paths relative to the project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALLPAPER_DIR = os.path.join(ROOT_DIR, "wallpapers")
THUMBS_DIR = os.path.join(ROOT_DIR, "thumbs")
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
AVAILABLE_MODES = ["video", "1min", "5min"]

def load_config():
    """Loads configuration from disk."""
    default_config = {
        "lively_path": DEFAULT_LIVELY_EXE,
        "mode": "video",
        "active_wallpapers": []
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Use current keys, fallback to defaults
            config = {
                "lively_path": data.get("lively_path", default_config["lively_path"]),
                "mode": data.get("mode", default_config["mode"]),
                "active_wallpapers": data.get("active_wallpapers", default_config["active_wallpapers"])
            }
            
            if config["mode"] not in AVAILABLE_MODES:
                config["mode"] = "video"
                
            return config
        except Exception as e:
            log(f"Error loading config: {e}")
            
    return default_config

def save_config(config_data):
    """Saves the current configuration to disk."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"Error saving config: {e}")

# Initial load
config = load_config()
