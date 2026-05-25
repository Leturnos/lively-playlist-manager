import ctypes

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

def is_user_gaming_or_focused() -> bool:
    """
    Checks if the user is currently in a fullscreen application (e.g., gaming).
    Ignores common desktop elements and specific overlays like TMainBox.
    """
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return False
            
        class_name = ctypes.create_string_buffer(255)
        ctypes.windll.user32.GetClassNameA(hwnd, class_name, 255)
        name = class_name.value.decode("utf-8", errors="ignore")
        
        # Desktop elements and specific iTop Easy Desktop class that shouldn't trigger "gaming" mode
        ignored_classes = ["WorkerW", "Progman", "Shell_TrayWnd", "TMainBox"]
        if name in ignored_classes:
            return False
            
        rect = RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)
        
        return width >= screen_w and height >= screen_h
    except Exception:
        return False
