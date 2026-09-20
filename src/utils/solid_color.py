import os
import re
import sys
import uuid
import ctypes
from PIL import Image
from src.config import config, save_config, SOLID_BACKGROUND_PATH
from src.utils.logger import log

def get_screen_resolution() -> tuple[int, int]:
    """Retrieves the primary screen resolution via Windows API, falling back to 1920x1080."""
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            # 0 = SM_CXSCREEN, 1 = SM_CYSCREEN
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            if w > 0 and h > 0:
                return (w, h)
        except Exception as e:
            log(f"Warning: Could not get screen metrics: {e}")
    return (1920, 1080)

def generate_solid_image(hex_color: str, output_path: str = SOLID_BACKGROUND_PATH) -> str:
    """Generates a solid color image at the native monitor resolution and atomically saves as PNG."""
    abs_output = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)

    # Validate hex color format, fallback to #18181b if malformed
    clean_hex = hex_color.strip() if isinstance(hex_color, str) else ""
    if not re.match(r"^#[0-9a-fA-F]{6}$", clean_hex):
        log(f"Invalid hex color '{hex_color}', defaulting to #18181b")
        clean_hex = "#18181b"

    w, h = get_screen_resolution()
    img = Image.new("RGB", (w, h), clean_hex)
    
    # Save atomically via a unique temporary file to avoid file lock collisions with OS/DWM
    unique_suffix = uuid.uuid4().hex[:6]
    tmp_path = f"{abs_output}.{unique_suffix}.tmp"
    try:
        img.save(tmp_path, "PNG")
        os.replace(tmp_path, abs_output)
    except Exception as e:
        log(f"Error saving solid image atomically: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise
    return abs_output

def apply_desktop_wallpaper(image_path: str) -> bool:
    """Applies an image as the native Windows desktop wallpaper via SystemParametersInfoW."""
    if sys.platform != "win32":
        return False

    abs_path = os.path.abspath(image_path)
    if not os.path.exists(abs_path) or os.path.getsize(abs_path) == 0:
        log(f"Wallpaper image does not exist or is empty: {abs_path}")
        return False

    try:
        # SPI_SETDESKWALLPAPER = 20
        # SPIF_UPDATEINIFILE (0x01) | SPIF_SENDCHANGE (0x02) = 3
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, abs_path, 3)
        if result:
            log(f"Desktop wallpaper updated to solid color: {abs_path}")
            return True
        else:
            err = ctypes.GetLastError()
            log(f"Warning: SystemParametersInfoW returned 0 (Win32 Error: {err})")
            return False
    except Exception as e:
        log(f"Error applying desktop wallpaper: {e}")
        return False

def apply_solid_background(hex_color: str) -> bool:
    """
    Generates the solid color image, updates the desktop wallpaper,
    updates lockscreen (if lockscreen sync with video is inactive),
    and persists the setting in config.
    """
    try:
        img_path = generate_solid_image(hex_color)
        wp_ok = apply_desktop_wallpaper(img_path)

        # If sync_lockscreen is disabled or before a video is played, apply to lock screen
        if not config.get("sync_lockscreen", False):
            try:
                # Lazy import to prevent pulling heavy moviepy dependency in non-video contexts
                from src.utils.lockscreen import set_lockscreen_registry
                set_lockscreen_registry(img_path)
            except Exception as e:
                log(f"Warning updating lockscreen with solid color: {e}")

        config["solid_background_color"] = hex_color.lower()
        save_config(config)
        return wp_ok
    except Exception as e:
        log(f"Error applying solid background: {e}")
        return False
