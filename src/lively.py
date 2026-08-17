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

def set_lively_playback(play: bool) -> bool:
    """Toggles Lively playback state (pause/resume) globally."""
    lively_exe = config.get("lively_path")
    if not os.path.exists(lively_exe) or not is_lively_running():
        return False
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(
            [lively_exe, "app", "--play", "true" if play else "false"],
            startupinfo=si,
            timeout=5,
            capture_output=True,
            text=True
        )
        return True
    except Exception as e:
        log(f"ERROR toggling Lively playback: {e}")
        return False

def set_wallpaper(video_path: str, monitor: int | None = None) -> bool:
    """Sends a command to Lively.exe to change the current wallpaper, optionally targeting a specific monitor."""
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
        
        target_mon = monitor if monitor is not None else config.get("target_monitor")
        cmd = [lively_exe, "setwp", "--file", video_path]
        if target_mon is not None:
            cmd.extend(["--monitor", str(target_mon)])
            
        result = subprocess.run(
            cmd,
            startupinfo=si, 
            timeout=15, 
            capture_output=True, 
            text=True
        )
        
        if result.returncode != 0:
            log(f"Lively Error ({result.returncode}): {result.stderr.strip()}")
            return False
            
        # Update history stack
        if state.current_video:
            current_path = os.path.join(os.path.dirname(video_path), state.current_video)
            if state.is_going_back:
                state.is_going_back = False
            else:
                if not state.history or state.history[-1] != current_path:
                    state.history.append(current_path)
                    if len(state.history) > 50:
                        state.history.pop(0)
            
        state.current_video = os.path.basename(video_path)
        log(f"Wallpaper changed: {state.current_video}" + (f" (Monitor {target_mon})" if target_mon is not None else ""))
        return True
        
    except subprocess.TimeoutExpired:
        log("ERROR: Lively interaction timed out.")
        return False
    except Exception as e:
        log(f"ERROR setting wallpaper: {e}")
        return False

