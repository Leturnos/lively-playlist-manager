import ctypes
from ctypes import wintypes

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD)
    ]

MONITOR_DEFAULTTONEAREST = 2
SM_CMONITORS = 80
IGNORED_CLASSES = frozenset({"WorkerW", "Progman", "Shell_TrayWnd", "TMainBox", "Shell_SecondaryTrayWnd"})

def get_monitor_count() -> int:
    """Returns the total count of active display monitors on the system."""
    try:
        count = ctypes.windll.user32.GetSystemMetrics(SM_CMONITORS)
        return max(1, count)
    except Exception:
        return 1

def is_user_gaming_or_focused() -> bool:
    """
    Checks if the user is in a fullscreen app/game (on any monitor)
    or if the screen is locked/suspended.
    Uses zero-allocation Win32 API calls for ultra-low RAM and CPU usage.
    """
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            # No foreground window usually indicates lock screen (Win+L), UAC prompt or screen off
            return True

        class_name = ctypes.create_string_buffer(256)
        ctypes.windll.user32.GetClassNameA(hwnd, class_name, 256)
        name = class_name.value.decode("utf-8", errors="ignore")

        if name in IGNORED_CLASSES:
            return False

        rect = RECT()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False

        # Find the monitor where this foreground window resides
        h_monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if not h_monitor:
            return False

        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if not ctypes.windll.user32.GetMonitorInfoW(h_monitor, ctypes.byref(mi)):
            return False

        # Checks if window covers or exceeds the monitor's bounds
        is_fullscreen = (
            rect.left <= mi.rcMonitor.left and
            rect.top <= mi.rcMonitor.top and
            rect.right >= mi.rcMonitor.right and
            rect.bottom >= mi.rcMonitor.bottom
        )

        return is_fullscreen
    except Exception:
        return False
