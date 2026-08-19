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
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

def trigger_previous():
    """Triggers the engine to play the previous wallpaper in history."""
    if state.history:
        log("Hotkey pressed: Previous Wallpaper (Win+Alt+PgUp)")
        state.play_previous_event.set()
        state.skip_event.set()
    else:
        log("Hotkey pressed: Win+Alt+PgUp (no previous wallpaper in history)")

def trigger_next():
    """Triggers the engine to skip to the next wallpaper."""
    log("Hotkey pressed: Next Wallpaper (Win+Alt+PgDn)")
    state.skip_event.set()

def start_hotkey_listener():
    """
    Registers global hotkeys (Win+Alt+PgUp / Win+Alt+PgDn) and listens for them
    using the native Windows RegisterHotKey API with zero extra dependencies.
    """
    state.hotkey_thread_id = kernel32.GetCurrentThreadId()
    modifiers = MOD_WIN | MOD_ALT | MOD_NOREPEAT

    # Register Win + Alt + PgUp (Previous)
    res_prev = user32.RegisterHotKey(None, HOTKEY_ID_PREV, modifiers, VK_PRIOR)
    # Register Win + Alt + PgDn (Next)
    res_next = user32.RegisterHotKey(None, HOTKEY_ID_NEXT, modifiers, VK_NEXT)

    if not res_prev:
        log("WARNING: Failed to register hotkey Win+Alt+PgUp (might already be in use by another app).")
    if not res_next:
        log("WARNING: Failed to register hotkey Win+Alt+PgDn (might already be in use by another app).")

    if res_prev or res_next:
        log("Global hotkeys initialized: Win+Alt+PgUp (Previous), Win+Alt+PgDn (Next)")

    msg = wintypes.MSG()
    try:
        while not state.stop_event.is_set():
            # GetMessageW blocks efficiently until a message arrives (0 CPU usage)
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:
                break

            if msg.message == WM_HOTKEY:
                if msg.wParam == HOTKEY_ID_PREV:
                    trigger_previous()
                elif msg.wParam == HOTKEY_ID_NEXT:
                    trigger_next()

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except Exception as e:
        log(f"Error in hotkey listener: {e}")
    finally:
        if res_prev:
            user32.UnregisterHotKey(None, HOTKEY_ID_PREV)
        if res_next:
            user32.UnregisterHotKey(None, HOTKEY_ID_NEXT)
        log("Global hotkeys unregistered.")
