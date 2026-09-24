import os
import re
import sys
import uuid
import ctypes
from PIL import Image
from src.config import config, save_config, SOLID_BACKGROUND_PATH
from src.utils.logger import log

if sys.platform == "win32":
    import winreg

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

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Converts a hex color string (e.g. '#18181b') to an (r, g, b) tuple."""
    clean_hex = hex_color.strip() if isinstance(hex_color, str) else ""
    if not re.match(r"^#[0-9a-fA-F]{6}$", clean_hex):
        clean_hex = "#18181b"
    return (
        int(clean_hex[1:3], 16),
        int(clean_hex[3:5], 16),
        int(clean_hex[5:7], 16)
    )

def apply_native_solid_color(hex_color: str) -> bool:
    """
    Configures Windows native solid desktop background color via Win32 API and Registry.
    This ensures that Windows DWM and Explorer natively start with this background color
    on boot/logon without waiting for background apps to start.
    """
    if sys.platform != "win32":
        return False

    r, g, b = hex_to_rgb(hex_color)
    rgb_str = f"{r} {g} {b}"
    colorref = (b << 16) | (g << 8) | r

    try:
        # COLOR_BACKGROUND = 1
        ctypes.windll.user32.SetSysColors(
            1,
            ctypes.byref(ctypes.c_int(1)),
            ctypes.byref(ctypes.c_ulong(colorref))
        )
    except Exception as e:
        log(f"Warning: SetSysColors failed: {e}")

    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\Colors", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "Background", 0, winreg.REG_SZ, rgb_str)

        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Wallpapers", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "BackgroundType", 0, winreg.REG_DWORD, 1)

        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "0")
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
        return True
    except Exception as e:
        log(f"Warning: Failed setting native solid color in registry: {e}")
        return False

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
    Generates the solid color image, updates native Windows desktop color,
    updates desktop wallpaper image fallback, updates lockscreen (if sync is inactive),
    and persists setting in config.
    """
    try:
        # 1. Configure native Windows solid background
        apply_native_solid_color(hex_color)

        # 2. Generate and apply image for shell / lockscreen fallback
        img_path = generate_solid_image(hex_color)
        wp_ok = apply_desktop_wallpaper(img_path)

        # 3. If sync_lockscreen is disabled or before a video is played, apply to lock screen
        if not config.get("sync_lockscreen", False):
            try:
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

def ensure_solid_background_configured() -> bool:
    """
    Ensures that the Windows registry reflects the configured solid background color.
    No-op if already configured, preventing disk I/O and process churn on startup.
    """
    if sys.platform != "win32":
        return False

    configured_hex = config.get("solid_background_color", "#18181b")
    r, g, b = hex_to_rgb(configured_hex)
    expected_rgb_str = f"{r} {g} {b}"

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Colors", 0, winreg.KEY_QUERY_VALUE) as key:
            current_color, _ = winreg.QueryValueEx(key, "Background")
            if current_color.strip() == expected_rgb_str:
                return True
    except Exception:
        pass

    # Mismatch or not yet configured - apply fully
    return apply_solid_background(configured_hex)

