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

LIVELY_APP_DATA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Lively Wallpaper")
LIVELY_SETTINGS_PATH = os.path.join(LIVELY_APP_DATA, "Settings.json")
LIVELY_LAYOUT_PATH = os.path.join(LIVELY_APP_DATA, "WallpaperLayout.json")

_lively_pause_cache = {
    "mtime": 0.0,
    "rules": {
        "algorithm": 3,
        "tile_size": 50,
        "coverage_threshold": 0.05,
        "app_focus_pause": 0,
        "app_fullscreen_pause": 1,
        "battery_pause": 0,
        "display_pause_settings": 0
    }
}

def get_lively_pause_rules(force_reload: bool = False) -> dict:
    """
    Reads pause and process monitor performance rules from Lively's Settings.json.
    Caches parsed rules and invalidates based on file mtime.
    """
    global _lively_pause_cache
    if not os.path.exists(LIVELY_SETTINGS_PATH):
        return dict(_lively_pause_cache["rules"])

    try:
        current_mtime = os.path.getmtime(LIVELY_SETTINGS_PATH)
        if force_reload or current_mtime != _lively_pause_cache["mtime"]:
            with open(LIVELY_SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            _lively_pause_cache["mtime"] = current_mtime
            _lively_pause_cache["rules"] = {
                "algorithm": int(data.get("ProcessMonitorAlgorithm", 3)),
                "tile_size": max(10, int(data.get("ProcessMonitorGridTileSize", 50))),
                "coverage_threshold": float(data.get("ProcessMonitorGridTileCoverageThreshold", 0.05)),
                "app_focus_pause": int(data.get("AppFocusPause", 0)),
                "app_fullscreen_pause": int(data.get("AppFullscreenPause", 1)),
                "battery_pause": int(data.get("BatteryPause", 0)),
                "display_pause_settings": int(data.get("DisplayPauseSettings", 0))
            }
    except Exception as e:
        log(f"Warning reading Lively pause rules: {e}")

    return dict(_lively_pause_cache["rules"])

def is_lively_running() -> bool:
    """Checks if Lively Wallpaper process is active."""
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] and "lively" in proc.info["name"].lower():
            return True
    return False

def open_lively_gui() -> bool:
    """Brings the Lively Wallpaper GUI window to the foreground."""
    lively_exe = config.get("lively_path")
    if not os.path.exists(lively_exe):
        log(f"ERROR: Lively.exe not found at: {lively_exe}")
        return False
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen([lively_exe, "app", "--showApp", "true"], startupinfo=si)
        return True
    except Exception as e:
        log(f"ERROR opening Lively GUI: {e}")
        return False

def get_lively_monitors() -> list[dict]:
    """
    Reads monitor information from Lively's WallpaperLayout.json or Settings.json.
    Returns a list of dicts: [{"index": 1, "name": "...", "is_primary": True, "bounds": "..."}]
    """
    monitors = []
    if os.path.exists(LIVELY_LAYOUT_PATH):
        try:
            with open(LIVELY_LAYOUT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                screen = item.get("LivelyScreen", {})
                idx = screen.get("Index")
                name = screen.get("DisplayName", f"Monitor {idx}")
                is_primary = screen.get("IsPrimary", False)
                bounds = screen.get("Bounds", "")
                if idx is not None:
                    monitors.append({
                        "index": idx,
                        "name": name,
                        "is_primary": is_primary,
                        "bounds": bounds
                    })
        except Exception as e:
            log(f"Error reading Lively WallpaperLayout.json: {e}")

    # Fallback to Settings.json SelectedDisplay if layout was empty
    if not monitors and os.path.exists(LIVELY_SETTINGS_PATH):
        try:
            with open(LIVELY_SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            screen = settings.get("SelectedDisplay", {})
            idx = screen.get("Index", 1)
            name = screen.get("DisplayName", f"Monitor {idx}")
            is_primary = screen.get("IsPrimary", True)
            monitors.append({
                "index": idx,
                "name": name,
                "is_primary": is_primary,
                "bounds": screen.get("Bounds", "")
            })
        except Exception as e:
            log(f"Error reading Lively Settings.json: {e}")

    if not monitors:
        monitors.append({
            "index": 1,
            "name": "Monitor Principal",
            "is_primary": True,
            "bounds": ""
        })

    return sorted(monitors, key=lambda m: m["index"])

def get_active_lively_monitor() -> int | None:
    """Returns the screen Index currently configured as SelectedDisplay in Lively's Settings.json."""
    if os.path.exists(LIVELY_SETTINGS_PATH):
        try:
            with open(LIVELY_SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            screen = settings.get("SelectedDisplay", {})
            return screen.get("Index")
        except Exception:
            pass
    return None

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

def set_wallpaper(video_path: str, monitor: int | str | None = None) -> bool:
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
        effective_mon = None

        if target_mon in (None, "auto"):
            # Check wallpaper arrangement in Lively
            arrangement = 0
            if os.path.exists(LIVELY_SETTINGS_PATH):
                try:
                    with open(LIVELY_SETTINGS_PATH, "r", encoding="utf-8") as f:
                        arrangement = json.load(f).get("WallpaperArrangement", 0)
                except Exception:
                    pass

            if arrangement == 0:
                # Per-display mode: follow Lively's active monitor
                effective_mon = get_active_lively_monitor()
            else:
                # Span or duplicate: omit monitor so Lively applies to all
                effective_mon = None
        else:
            try:
                effective_mon = int(target_mon)
            except (ValueError, TypeError):
                effective_mon = None

        cmd = [lively_exe, "setwp", "--file", video_path]
        if effective_mon is not None:
            cmd.extend(["--monitor", str(effective_mon)])
            
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
        mon_str = f" (Monitor {effective_mon})" if effective_mon is not None else " (Auto/All Monitors)"
        log(f"Wallpaper changed: {state.current_video}{mon_str}")
        return True
        
    except subprocess.TimeoutExpired:
        log("ERROR: Lively interaction timed out.")
        return False
    except Exception as e:
        log(f"ERROR setting wallpaper: {e}")
        return False

