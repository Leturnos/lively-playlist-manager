import ctypes
from ctypes import wintypes
import threading
from src import state
from src.utils.logger import log

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 Hotkey Modifiers
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Virtual Key Codes
VK_PRIOR = 0x21  # Page Up
VK_NEXT = 0x22   # Page Down

# Hotkey IDs
HOTKEY_ID_PREV = 1
HOTKEY_ID_NEXT = 2

# Window and Power Messages
WM_HOTKEY = 0x0312
WM_POWERBROADCAST = 0x0218
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
WM_QUIT = 0x0012
WM_DESTROY = 0x0002

# Power Broadcast Events
PBT_POWERSETTINGCHANGE = 0x8013
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMEAUTOMATIC = 0x0012
PBT_APMRESUMESUSPEND = 0x0007

# Win32 Structures
class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_byte * 8)
    ]

class POWERBROADCAST_SETTING(ctypes.Structure):
    _fields_ = [
        ("PowerSetting", GUID),
        ("DataLength", wintypes.DWORD),
        ("Data", ctypes.c_byte * 4)
    ]

# Power Setting GUIDs
# GUID_CONSOLE_DISPLAY_STATE: 238C9FA8-0AAD-41ED-8394-4976E8B63F9F
GUID_CONSOLE_DISPLAY_STATE = GUID(
    0x238C9FA8, 0x0AAD, 0x41ED, (ctypes.c_byte * 8)(0x83, 0x94, 0x49, 0x76, 0xE8, 0xB6, 0x3F, 0x9F)
)
# GUID_SESSION_DISPLAY_STATUS: 2B84762E-4CBE-4602-AF9A-7605709EC3E5
GUID_SESSION_DISPLAY_STATUS = GUID(
    0x2B84762E, 0x4CBE, 0x4602, (ctypes.c_byte * 8)(0xAF, 0x9A, 0x76, 0x05, 0x70, 0x9E, 0xC3, 0xE5)
)

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
PHANDLER_ROUTINE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

# Win32 API 64-bit safe prototypes
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_longlong
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
user32.CreateWindowExW.restype = wintypes.HWND

try:
    user32.RegisterPowerSettingNotification.argtypes = [wintypes.HANDLE, ctypes.POINTER(GUID), wintypes.DWORD]
    user32.RegisterPowerSettingNotification.restype = wintypes.HANDLE
    user32.UnregisterPowerSettingNotification.argtypes = [wintypes.HANDLE]
    user32.UnregisterPowerSettingNotification.restype = wintypes.BOOL
except AttributeError:
    pass

kernel32.SetConsoleCtrlHandler.argtypes = [PHANDLER_ROUTINE, wintypes.BOOL]
kernel32.SetConsoleCtrlHandler.restype = wintypes.BOOL

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HICON),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON)
    ]

def trigger_previous():
    """Triggers the engine to play the previous wallpaper in history or sequential order."""
    log("Hotkey pressed: Previous Wallpaper (Win+Alt+PgUp)")
    state.play_previous_event.set()
    state.skip_event.set()

def trigger_next():
    """Triggers the engine to skip to the next wallpaper."""
    log("Hotkey pressed: Next Wallpaper (Win+Alt+PgDn)")
    state.skip_event.set()

def handle_system_message(msg: int, wparam: int, lparam: int | None = None, display_state: int | None = None) -> int:
    """
    Handles native Windows system messages for power state changes (display on/off, sleep)
    and shutdown/logoff notifications. Returns message processing result.
    """
    if msg == WM_POWERBROADCAST:
        if wparam == PBT_POWERSETTINGCHANGE:
            val = display_state
            if val is None and lparam:
                try:
                    setting = ctypes.cast(lparam, ctypes.POINTER(POWERBROADCAST_SETTING)).contents
                    val = int.from_bytes(bytes(setting.Data[:min(setting.DataLength, 4)]), "little")
                except Exception as e:
                    log(f"Warning reading power setting data: {e}")
            if val is not None:
                if val == 0:
                    state.is_display_off = True
                    log("Display turned OFF (power management). Rotation paused.")
                else:
                    state.is_display_off = False
                    log("Display turned ON. Rotation resumed.")
        elif wparam == PBT_APMSUSPEND:
            state.is_display_off = True
            log("System suspend detected. Rotation paused.")
        elif wparam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND):
            state.is_display_off = False
            log("System resume detected. Rotation resumed.")
        return 1

    elif msg == WM_QUERYENDSESSION:
        log("System shutdown/logoff initiated (WM_QUERYENDSESSION). Stopping rotation engine immediately.")
        state.is_system_shutting_down = True
        state.stop_event.set()
        return 1

    elif msg == WM_ENDSESSION:
        if wparam != 0:
            log("System session ending (WM_ENDSESSION). Stopping rotation engine immediately.")
            state.is_system_shutting_down = True
            state.stop_event.set()
        return 0

    return 0

def handle_console_ctrl(ctrl_type: int) -> bool:
    """
    Console control handler to catch shutdown and logoff events immediately.
    """
    # CTRL_CLOSE_EVENT = 2, CTRL_LOGOFF_EVENT = 5, CTRL_SHUTDOWN_EVENT = 6
    if ctrl_type in (2, 5, 6):
        log(f"System shutdown/logoff detected via ConsoleCtrl (type={ctrl_type}). Stopping engine.")
        state.is_system_shutting_down = True
        state.stop_event.set()
        return True
    return False

# Persistent references to prevent garbage collection of callbacks
_global_wndproc_cb = None
_global_ctrl_cb = None

def start_hotkey_listener():
    """
    Registers a hidden Win32 window to listen for:
    1. Global hotkeys (Win+Alt+PgUp / Win+Alt+PgDn)
    2. Display state changes (screen off after idle timeout / screen on)
    3. System shutdown / restart / logoff notifications (WM_QUERYENDSESSION / WM_ENDSESSION)
    4. Console close / shutdown signals via SetConsoleCtrlHandler.
    """
    global _global_wndproc_cb, _global_ctrl_cb
    state.hotkey_thread_id = kernel32.GetCurrentThreadId()

    # Register console ctrl handler for shutdown/logoff
    _global_ctrl_cb = PHANDLER_ROUTINE(handle_console_ctrl)
    try:
        kernel32.SetConsoleCtrlHandler(_global_ctrl_cb, True)
    except Exception as e:
        log(f"Warning setting console ctrl handler: {e}")

    # Window procedure for the listener window
    def wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_HOTKEY:
            if wparam == HOTKEY_ID_PREV:
                trigger_previous()
            elif wparam == HOTKEY_ID_NEXT:
                trigger_next()
            return 0
        elif msg in (WM_POWERBROADCAST, WM_QUERYENDSESSION, WM_ENDSESSION):
            return handle_system_message(msg, wparam, lparam)
        elif msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    _global_wndproc_cb = WNDPROC(wndproc)

    # Register class and create message window
    class_name = "LivelyPlaylistSystemListener"
    hinstance = kernel32.GetModuleHandleW(None)

    wcls = WNDCLASSEXW()
    wcls.cbSize = ctypes.sizeof(WNDCLASSEXW)
    wcls.lpfnWndProc = _global_wndproc_cb
    wcls.lpszClassName = class_name
    wcls.hInstance = hinstance

    atom = user32.RegisterClassExW(ctypes.byref(wcls))
    hwnd = user32.CreateWindowExW(
        0, class_name, "LivelyPlaylistListener", 0, 0, 0, 0, 0, None, None, hinstance, None
    )

    modifiers = MOD_WIN | MOD_ALT | MOD_NOREPEAT
    res_prev = user32.RegisterHotKey(hwnd, HOTKEY_ID_PREV, modifiers, VK_PRIOR)
    res_next = user32.RegisterHotKey(hwnd, HOTKEY_ID_NEXT, modifiers, VK_NEXT)

    if not res_prev:
        log("WARNING: Failed to register hotkey Win+Alt+PgUp (might already be in use).")
    if not res_next:
        log("WARNING: Failed to register hotkey Win+Alt+PgDn (might already be in use).")
    if res_prev or res_next:
        log("Global hotkeys initialized: Win+Alt+PgUp (Previous), Win+Alt+PgDn (Next)")

    # Register for display power state notifications (screen turned off / on)
    h_power_console = None
    h_power_session = None
    try:
        h_power_console = user32.RegisterPowerSettingNotification(
            hwnd, ctypes.byref(GUID_CONSOLE_DISPLAY_STATE), 0
        )
        h_power_session = user32.RegisterPowerSettingNotification(
            hwnd, ctypes.byref(GUID_SESSION_DISPLAY_STATUS), 0
        )
        if h_power_console or h_power_session:
            log("Power setting notifications initialized (display state & power broadcast).")
    except Exception as e:
        log(f"Warning registering power setting notifications: {e}")

    msg = wintypes.MSG()
    try:
        while not state.stop_event.is_set() and not state.is_system_shutting_down:
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except Exception as e:
        log(f"Error in system listener loop: {e}")
    finally:
        try:
            if h_power_console:
                user32.UnregisterPowerSettingNotification(h_power_console)
            if h_power_session:
                user32.UnregisterPowerSettingNotification(h_power_session)
        except Exception:
            pass
        if res_prev:
            user32.UnregisterHotKey(hwnd, HOTKEY_ID_PREV)
        if res_next:
            user32.UnregisterHotKey(hwnd, HOTKEY_ID_NEXT)
        if hwnd:
            user32.DestroyWindow(hwnd)
        if atom:
            user32.UnregisterClassW(class_name, hinstance)
        log("System event listener and global hotkeys stopped.")
