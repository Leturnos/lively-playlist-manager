import os
import sys
import uuid
import json
import shutil
import threading
import winreg
from PIL import Image
from moviepy import VideoFileClip
from src.config import (
    LOCKSCREEN_PATH_A,
    LOCKSCREEN_PATH_B,
    STATIC_WALLPAPER_DIR,
    SOLID_BACKGROUND_PATH,
    LOCKSCREEN_FRAMES_DIR,
    LOCKSCREEN_STATE_FILE,
    WALLPAPER_DIR,
)
from src.utils.logger import log
from src import state

CSP_REG_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP"
POLICY_REG_KEY = r"SOFTWARE\Policies\Microsoft\Windows\Personalization"
REG_ACCESS_WRITE = winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
REG_ACCESS_READ = winreg.KEY_QUERY_VALUE | winreg.KEY_WOW64_64KEY

_sync_lock = threading.Lock()

def get_next_lockscreen_path() -> str:
    """
    Alternates between two distinct file paths (A/B ping-pong) to bust
    Windows lock screen caching. When the path string in the registry changes,
    Windows immediately refreshes and re-renders the new image.
    """
    if sys.platform == "win32":
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, CSP_REG_KEY, 0, REG_ACCESS_READ) as key:
                current_reg_val, _ = winreg.QueryValueEx(key, "LockScreenImagePath")
                if os.path.abspath(current_reg_val).lower() == os.path.abspath(LOCKSCREEN_PATH_A).lower():
                    return LOCKSCREEN_PATH_B
        except Exception:
            pass
    return LOCKSCREEN_PATH_A

def get_cached_frame_path(video_path: str) -> str:
    """Returns the persistent high-resolution frame cache path for a video."""
    basename = os.path.basename(video_path)
    return os.path.join(LOCKSCREEN_FRAMES_DIR, f"{basename}.jpg")

def extract_highres_frame(video_path: str, output_path: str) -> bool:
    """
    Extracts a high-resolution frame from a video and saves it atomically as a high-quality JPEG.
    Utilizes a persistent high-resolution frame cache in LOCKSCREEN_FRAMES_DIR to achieve
    sub-5ms lockscreen updates for previously seen or pre-cached wallpapers.
    """
    if not os.path.exists(video_path):
        log(f"Lockscreen: Video file not found: {video_path}")
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.makedirs(LOCKSCREEN_FRAMES_DIR, exist_ok=True)

    cached_frame = get_cached_frame_path(video_path)

    # Fast path: copy directly from frame cache (< 5ms)
    if os.path.exists(cached_frame) and os.path.getsize(cached_frame) > 0:
        try:
            shutil.copyfile(cached_frame, output_path)
            return True
        except Exception as e:
            log(f"Lockscreen: Warning copying from frame cache: {e}")

    # Slow path: extract frame via MoviePy and store in cache
    unique_suffix = uuid.uuid4().hex[:6]
    tmp_path = f"{output_path}.{unique_suffix}.tmp"

    clip = None
    try:
        clip = VideoFileClip(video_path)
        # Sample frame at 10% of duration (capped at 1.0s to avoid slow seeks on long videos)
        sample_time = min(1.0, clip.duration * 0.1) if clip.duration and clip.duration > 0 else 0
        frame = clip.get_frame(sample_time)
        
        img = Image.fromarray(frame)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
            
        img.save(tmp_path, "JPEG", quality=95)
        
        # Atomic replacement to avoid corrupt locks during OS read
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
            # Populate persistent cache first
            try:
                shutil.copyfile(tmp_path, cached_frame)
            except Exception as e:
                log(f"Lockscreen: Warning saving frame cache: {e}")

            os.replace(tmp_path, output_path)
            return True
        else:
            log("Lockscreen: Generated frame was empty or failed to save.")
            return False
    except Exception as e:
        log(f"Lockscreen: Error extracting frame from {video_path}: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False
    finally:
        if clip is not None:
            try:
                clip.close()
            except Exception:
                pass

def check_lockscreen_permissions() -> bool:
    """
    Checks if the current process has write access to PersonalizationCSP in HKLM.
    Returns True if writable, False if restricted.
    """
    if sys.platform != "win32":
        return False
    try:
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, CSP_REG_KEY, 0, REG_ACCESS_WRITE):
            return True
    except PermissionError:
        return False
    except Exception:
        return False

def set_lockscreen_registry(image_path: str) -> tuple[bool, str]:
    """
    Applies the image to Windows Lock Screen via PersonalizationCSP and Group Policy registry keys.
    Returns (success: bool, message: str). Never raises unhandled exceptions.
    """
    if sys.platform != "win32":
        return False, "Lockscreen configuration is only supported on Windows."

    abs_path = os.path.abspath(image_path)
    if not os.path.exists(abs_path) or os.path.getsize(abs_path) == 0:
        return False, f"Lockscreen image does not exist or is empty: {abs_path}"

    applied_csp = False
    applied_policy = False
    error_msg = ""

    # 1. Primary method: PersonalizationCSP (Windows 10/11 Home & Pro)
    try:
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, CSP_REG_KEY, 0, REG_ACCESS_WRITE) as key:
            winreg.SetValueEx(key, "LockScreenImagePath", 0, winreg.REG_SZ, abs_path)
            winreg.SetValueEx(key, "LockScreenImageUrl", 0, winreg.REG_SZ, abs_path)
            winreg.SetValueEx(key, "LockScreenImageStatus", 0, winreg.REG_DWORD, 1)
            applied_csp = True
    except PermissionError:
        error_msg = "Access denied to HKLM. Run setup_lockscreen_permission.bat as Administrator once to enable."
    except Exception as e:
        error_msg = f"Failed to set PersonalizationCSP: {e}"

    # 2. Secondary method: Policy key (Windows 10/11 Enterprise / Education fallback)
    try:
        with winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, POLICY_REG_KEY, 0, REG_ACCESS_WRITE) as key:
            winreg.SetValueEx(key, "LockScreenImage", 0, winreg.REG_SZ, abs_path)
            applied_policy = True
    except Exception:
        pass

    if applied_csp or applied_policy:
        return True, "Lockscreen registry updated successfully."
    else:
        return False, error_msg

def restore_lockscreen_registry() -> bool:
    """
    Restores the standard Windows lockscreen behavior or applies the configured
    solid background color image if available.
    """
    if sys.platform != "win32":
        return False

    if os.path.exists(SOLID_BACKGROUND_PATH) and os.path.getsize(SOLID_BACKGROUND_PATH) > 0:
        success, msg = set_lockscreen_registry(SOLID_BACKGROUND_PATH)
        if success:
            log("Lockscreen: Restored to configured solid background color.")
            return True
        else:
            log(f"Lockscreen: Could not apply solid background ({msg}), falling back to standard reset.")

    restored = False
    # Disable PersonalizationCSP
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, CSP_REG_KEY, 0, REG_ACCESS_WRITE) as key:
            winreg.SetValueEx(key, "LockScreenImageStatus", 0, winreg.REG_DWORD, 0)
            try:
                winreg.DeleteValue(key, "LockScreenImagePath")
            except FileNotFoundError:
                pass
            try:
                winreg.DeleteValue(key, "LockScreenImageUrl")
            except FileNotFoundError:
                pass
            restored = True
            log("Lockscreen: PersonalizationCSP policy cleared.")
    except PermissionError:
        log("Lockscreen: Permission denied when clearing PersonalizationCSP.")
    except FileNotFoundError:
        restored = True
    except Exception as e:
        log(f"Lockscreen: Error clearing PersonalizationCSP: {e}")

    # Clean up Group Policy LockScreenImage if present
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, POLICY_REG_KEY, 0, REG_ACCESS_WRITE) as key:
            try:
                winreg.DeleteValue(key, "LockScreenImage")
                log("Lockscreen: Group policy LockScreenImage cleared.")
            except FileNotFoundError:
                pass
    except Exception:
        pass

    return restored

def save_lockscreen_state(video_filename: str, image_path: str):
    """
    Persists the currently active lock screen image and corresponding video filename.
    Used during boot reconciliation to guarantee that desktop playback aligns
    with the exact wallpaper visible on the Windows lock screen.
    """
    os.makedirs(os.path.dirname(LOCKSCREEN_STATE_FILE), exist_ok=True)
    tmp_file = f"{LOCKSCREEN_STATE_FILE}.tmp"
    payload = {
        "wallpaper_filename": video_filename,
        "image_path": os.path.abspath(image_path),
        "timestamp": os.path.getmtime(image_path) if os.path.exists(image_path) else None,
    }
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, LOCKSCREEN_STATE_FILE)
    except Exception as e:
        log(f"Lockscreen: Error saving lockscreen state: {e}")
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass

def get_current_lockscreen_wallpaper() -> str | None:
    """
    Retrieves the video filename recorded in lockscreen_state.json if the video file
    actually exists in WALLPAPER_DIR. Returns None if invalid, missing, or deleted.
    """
    if not os.path.exists(LOCKSCREEN_STATE_FILE):
        return None

    try:
        with open(LOCKSCREEN_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        video_filename = data.get("wallpaper_filename")
        if not video_filename or not isinstance(video_filename, str):
            return None

        video_path = os.path.join(WALLPAPER_DIR, video_filename)
        if os.path.exists(video_path):
            return video_filename
    except Exception as e:
        log(f"Lockscreen: Error reading lockscreen state: {e}")

    return None

def sync_lockscreen_worker(video_path: str):
    """
    Worker task executed in a background thread to extract the frame and update lockscreen
    without delaying or freezing the main Lively playback engine.
    Serialized with a lock and guards against out-of-order execution from skipped videos.
    """
    with _sync_lock:
        # Avoid stale updates if user rapidly skipped to another video
        if state.current_video and os.path.basename(video_path) != state.current_video:
            return

        try:
            target_path = get_next_lockscreen_path()
            if not extract_highres_frame(video_path, target_path):
                return

            # Double-check staleness after potentially slow extraction
            if state.current_video and os.path.basename(video_path) != state.current_video:
                return

            success, msg = set_lockscreen_registry(target_path)
            if success:
                save_lockscreen_state(os.path.basename(video_path), target_path)
                log(f"Lockscreen synced with: {os.path.basename(video_path)} -> {os.path.basename(target_path)}")
            else:
                log(f"Lockscreen warning: {msg}")
        except Exception as e:
            log(f"Lockscreen: Unexpected error in sync worker: {e}")

