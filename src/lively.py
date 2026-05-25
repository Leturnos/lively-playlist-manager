import os
import subprocess
import psutil
import glob
import json
import shutil
import time
from src.config import config, LIVELY_LIBRARY, LIVELY_WPTMP
from src.utils.logger import log
from src import state

def is_lively_running() -> bool:
    """Checks if Lively Wallpaper process is active."""
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] and "lively" in proc.info["name"].lower():
            return True
    return False

def clear_library_videos():
    """
    Clears video wallpapers from the local Lively library to prevent storage bloat.
    Type 7 refers to video wallpapers in Lively's internal schema.
    """
    for root in [LIVELY_LIBRARY, LIVELY_WPTMP]:
        if not os.path.exists(root):
            continue
        for folder in glob.glob(os.path.join(root, "*")):
            info_path = os.path.join(folder, "LivelyInfo.json")
            if not os.path.exists(info_path):
                continue
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                if info.get("Type") == 7:
                    shutil.rmtree(folder, ignore_errors=True)
            except Exception:
                continue

def set_wallpaper(video_path: str) -> bool:
    """Sends a command to Lively.exe to change the current wallpaper."""
    lively_exe = config.get("lively_path")
    
    if not os.path.exists(lively_exe):
        log(f"ERROR: Lively.exe not found at: {lively_exe}")
        return False
        
    if not is_lively_running():
        log("Lively is not running. Starting...")
        subprocess.Popen([lively_exe])
        time.sleep(4)
        
    if not os.path.exists(video_path):
        log(f"ERROR: Video file not found: {video_path}")
        return False
        
    try:
        # Prevent console window from popping up
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        clear_library_videos()
        
        result = subprocess.run(
            [lively_exe, "setwp", "--file", video_path],
            startupinfo=si, 
            timeout=15, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            log(f"Lively Error ({result.returncode}): {result.stderr.strip()}")
            return False
            
        state.current_video = os.path.basename(video_path)
        log(f"Wallpaper changed: {state.current_video}")
        return True
        
    except subprocess.TimeoutExpired:
        log("ERROR: Lively interaction timed out.")
        return False
    except Exception as e:
        log(f"ERROR setting wallpaper: {e}")
        return False
