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

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", wintypes.BYTE),
        ("BatteryFlag", wintypes.BYTE),
        ("BatteryLifePercent", wintypes.BYTE),
        ("SystemStatusFlag", wintypes.BYTE),
        ("BatteryLifeTime", wintypes.DWORD),
        ("BatteryFullLifeTime", wintypes.DWORD),
    ]

MONITOR_DEFAULTTONEAREST = 2
SM_CMONITORS = 80
DWMWA_CLOAKED = 14
IGNORED_CLASSES = frozenset({
    # Desktop
    "WorkerW",
    "Progman",
    # Start menu, taskview (Win10), action center, search flyouts
    "Windows.UI.Core.CoreWindow",
    # Taskview (Win11), Start menu (Win11), XAML island hosts
    "XamlExplorerHostIslandWindow",
    # Alt+tab screen (Win10)
    "MultitaskingViewFrame",
    # Widget window (Win11)
    "WindowsDashboard",
    # Taskbars
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    # Systray notifyicon expanded popup / flyouts
    "NotifyIconOverflowWindow",
    "TopLevelWindowForOverflowXamlIsland",
    # Third-party desktop widgets / legacy tools
    "RainmeterMeterWindow",
    "_cls_desk_",
    "TMainBox",
})

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM
)

def get_monitor_count() -> int:
    """Returns the total count of active display monitors on the system."""
    try:
        count = ctypes.windll.user32.GetSystemMetrics(SM_CMONITORS)
        return max(1, count)
    except Exception:
        return 1

def is_on_battery() -> bool:
    """Returns True if the system is running on battery power (AC offline)."""
    try:
        sps = SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
            return sps.ACLineStatus == 0
    except Exception:
        pass
    return False

def is_rect_covering(rect: tuple[int, int, int, int], target: tuple[int, int, int, int], threshold: float = 0.95) -> bool:
    """
    Checks if a window rect covers at least `threshold` (e.g. 95%) of the target area.
    Matches Lively's WindowUtil.IsWindowCoveringTarget.
    """
    r_left, r_top, r_right, r_bottom = rect
    t_left, t_top, t_right, t_bottom = target

    inter_left = max(r_left, t_left)
    inter_top = max(r_top, t_top)
    inter_right = min(r_right, t_right)
    inter_bottom = min(r_bottom, t_bottom)

    if inter_right <= inter_left or inter_bottom <= inter_top:
        return False

    inter_area = (inter_right - inter_left) * (inter_bottom - inter_top)
    target_area = (t_right - t_left) * (t_bottom - t_top)
    if target_area <= 0:
        return False

    return (inter_area / float(target_area)) >= threshold

def is_grid_covered(work_area: tuple[int, int, int, int],
                    window_rects: list[tuple[int, int, int, int]],
                    tile_size: int = 50,
                    coverage_threshold: float = 0.05,
                    hwnds: list[int] | None = None) -> bool:
    """
    Evaluates whether the screen area is covered by windows using the Grid algorithm.

    Mirrors Lively's IsDisplayCoveredByWindowGrid:
    1. Fast-path: if any window is OS-maximized (IsZoomed), return True immediately.
       Falls back to geometric ≥95% coverage check when hwnd list is unavailable.
    2. Tile check: divides work_area into tile_size×tile_size blocks and checks if
       each tile center is covered. Returns True if uncovered ratio ≤ coverage_threshold.
    """
    left, top, right, bottom = work_area
    w = right - left
    h = bottom - top
    if w <= 0 or h <= 0:
        return False

    # Fast-path: mirrors Lively's `topLevelWindows.Exists(NativeMethods.IsZoomed)`
    if hwnds:
        for hwnd in hwnds:
            try:
                if ctypes.windll.user32.IsZoomed(hwnd):
                    return True
            except Exception:
                pass
    else:
        # Fallback when hwnds are unavailable: geometric coverage check
        for rect in window_rects:
            if is_rect_covering(rect, work_area, 0.95):
                return True

    tile_size = max(10, tile_size)
    cols = max(1, (w + tile_size - 1) // tile_size)
    rows = max(1, (h + tile_size - 1) // tile_size)
    total_tiles = cols * rows

    covered_count = 0

    for r in range(rows):
        py = top + r * tile_size + tile_size // 2
        if py >= bottom:
            py = bottom - 1
        for c in range(cols):
            px = left + c * tile_size + tile_size // 2
            if px >= right:
                px = right - 1

            for (w_left, w_top, w_right, w_bottom) in window_rects:
                if w_left <= px < w_right and w_top <= py < w_bottom:
                    covered_count += 1
                    break

    uncovered_ratio = (total_tiles - covered_count) / float(total_tiles)
    return uncovered_ratio <= coverage_threshold

def get_visible_windows(
    target_monitor_rect: tuple[int, int, int, int] | None = None,
    include_hwnds: bool = False,
) -> list[tuple[int, int, int, int]] | list[tuple[tuple[int, int, int, int], int]]:
    """
    Enumerates top-level visible windows, filtering out minimized, cloaked,
    and shell/desktop windows.

    Args:
        target_monitor_rect: When provided, only windows intersecting this rect are returned.
        include_hwnds: When True, returns list of (rect, hwnd) tuples instead of just rects.

    Returns:
        List of (left, top, right, bottom) rects, or (rect, hwnd) tuples if include_hwnds=True.
    """
    windows = []

    def enum_cb(hwnd, lparam):
        try:
            if not ctypes.windll.user32.IsWindowVisible(hwnd):
                return True
            if ctypes.windll.user32.IsIconic(hwnd):
                return True

            cloaked = wintypes.DWORD()
            res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
                hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
            )
            if res == 0 and cloaked.value != 0:
                return True

            class_name = ctypes.create_string_buffer(256)
            ctypes.windll.user32.GetClassNameA(hwnd, class_name, 256)
            name = class_name.value.decode("utf-8", errors="ignore")
            if name in IGNORED_CLASSES:
                return True

            # Ignore windows with no title (e.g. background helper windows, tooltips, hidden message anchors)
            if ctypes.windll.user32.GetWindowTextLengthW(hwnd) == 0:
                return True

            # Ignore tool windows and transparent click-through layered windows (matches Lively IsVisibleTopLevelWindows)
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE = -20
            if ex_style & 0x00000080:  # WS_EX_TOOLWINDOW
                return True
            if (ex_style & 0x00080000) and (ex_style & 0x00000020):  # WS_EX_LAYERED and WS_EX_TRANSPARENT
                return True

            rect = RECT()
            if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                # Ignore invisible/tiny helper windows (e.g. 16x16 event targets, 1x1 helpers)
                if (rect.right - rect.left) > 20 and (rect.bottom - rect.top) > 20:
                    if target_monitor_rect:
                        m_left, m_top, m_right, m_bottom = target_monitor_rect
                        if not (rect.right <= m_left or rect.left >= m_right or
                                rect.bottom <= m_top or rect.top >= m_bottom):
                            entry = (rect.left, rect.top, rect.right, rect.bottom)
                            windows.append((entry, hwnd) if include_hwnds else entry)
                    else:
                        entry = (rect.left, rect.top, rect.right, rect.bottom)
                        windows.append((entry, hwnd) if include_hwnds else entry)
        except Exception:
            pass
        return True

    cb = WNDENUMPROC(enum_cb)
    hdesk = None
    try:
        hdesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x0100 | 0x0040 | 0x0004 | 0x0001 | 0x0002)
    except Exception:
        pass

    if hdesk:
        try:
            ctypes.windll.user32.SetThreadDesktop(hdesk)
            ctypes.windll.user32.EnumDesktopWindows(hdesk, cb, 0)
        finally:
            ctypes.windll.user32.CloseDesktop(hdesk)
    else:
        ctypes.windll.user32.EnumWindows(cb, 0)

    return windows


def get_system_monitors() -> list[dict]:
    """
    Returns list of active monitors with their bounds and work area.
    """
    monitors = []

    def enum_cb(hmon, hdc, lprect, lparam):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if ctypes.windll.user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            is_primary = bool(mi.dwFlags & 1)
            monitors.append({
                "hmonitor": hmon,
                "rect": (mi.rcMonitor.left, mi.rcMonitor.top, mi.rcMonitor.right, mi.rcMonitor.bottom),
                "work": (mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom),
                "is_primary": is_primary
            })
        return True

    cb = MONITORENUMPROC(enum_cb)
    ctypes.windll.user32.EnumDisplayMonitors(None, None, cb, 0)

    for idx, m in enumerate(monitors, 1):
        m["index"] = idx
    return monitors

def is_system_locked() -> bool:
    """
    Checks if Windows is locked (Win+L) or at a secure desktop (UAC).
    OpenInputDesktop returns 0 (Access Denied) when locked.
    """
    try:
        hdesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x0100)
        if not hdesk:
            return True
        ctypes.windll.user32.CloseDesktop(hdesk)
    except Exception:
        pass
    return False

def is_user_gaming_or_focused() -> bool:
    """
    Fallback check: checks if foreground window is fullscreen on any monitor
    or if screen is locked.
    """
    try:
        if is_system_locked():
            return True

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return False

        class_name = ctypes.create_string_buffer(256)
        ctypes.windll.user32.GetClassNameA(hwnd, class_name, 256)
        name = class_name.value.decode("utf-8", errors="ignore")
        if name in IGNORED_CLASSES:
            return False

        rect = RECT()
        if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False

        h_monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        if not h_monitor:
            return False

        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if not ctypes.windll.user32.GetMonitorInfoW(h_monitor, ctypes.byref(mi)):
            return False

        return (
            rect.left <= mi.rcMonitor.left and
            rect.top <= mi.rcMonitor.top and
            rect.right >= mi.rcMonitor.right and
            rect.bottom >= mi.rcMonitor.bottom
        )
    except Exception:
        return False

def should_pause_for_lively() -> bool:
    """
    Determines if rotation playback should pause dynamically synchronizing
    with Lively Wallpaper's exact performance rules:
    - Screen locked / UAC prompt / screen off
    - Battery pause (BatteryPause == AppRules.pause == 0)
    - Fullscreen/Focus evaluation according to ProcessMonitorAlgorithm:
        0 (foreground): checks foreground window focus / maximized / >=95% coverage
        1 (all): checks all visible windows for maximized / >=95% coverage
        2 (gamemode): checks Direct3D fullscreen game state via SHQueryUserNotificationState
        3 (grid): evaluates 50px grid coverage, single maximized, or app focus pause
      All window-based pauses require AppFullscreenPause == AppRules.pause == 0 (Lively Playback.cs).
    """
    try:
        if is_system_locked():
            return True

        from src.lively import get_lively_pause_rules, LIVELY_APP_RULE_PAUSE
        rules = get_lively_pause_rules()

        # 1. Battery check (independent of window states)
        # In Lively C# enum AppRules: pause = 0, ignore = 1, kill = 2
        if rules.get("battery_pause", 1) == LIVELY_APP_RULE_PAUSE and is_on_battery():
            return True

        # In Lively Playback.cs:
        # var isFullScreenPause = userSettings.Settings.AppFullscreenPause == AppRules.pause; // 0
        # var isFocusedAppPause = userSettings.Settings.AppFocusPause == AppRules.pause;      // 0
        is_fullscreen_pause = (rules.get("app_fullscreen_pause", LIVELY_APP_RULE_PAUSE) == LIVELY_APP_RULE_PAUSE)
        is_focus_pause = (rules.get("app_focus_pause", 1) == LIVELY_APP_RULE_PAUSE)

        # If AppFullscreenPause is set to ignore (1), Lively NEVER pauses for open apps
        if not is_fullscreen_pause:
            return False

        from src.config import config
        target_mon = config.get("target_monitor")

        sys_monitors = get_system_monitors()
        if not sys_monitors:
            return is_user_gaming_or_focused()

        eval_monitors = []
        if rules.get("display_pause_settings", 0) == 1:
            eval_monitors = sys_monitors
        elif target_mon in (None, "auto"):
            primary_mons = [m for m in sys_monitors if m["is_primary"]]
            eval_monitors = primary_mons if primary_mons else [sys_monitors[0]]
        else:
            try:
                target_idx = int(target_mon)
                matched = [m for m in sys_monitors if m["index"] == target_idx]
                eval_monitors = matched if matched else [sys_monitors[0]]
            except (ValueError, TypeError):
                eval_monitors = [sys_monitors[0]]

        # Ensure calling thread has access to the interactive desktop for foreground window
        try:
            hdesk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x0100 | 0x0040 | 0x0004 | 0x0001 | 0x0002)
            if hdesk:
                try:
                    ctypes.windll.user32.SetThreadDesktop(hdesk)
                finally:
                    ctypes.windll.user32.CloseDesktop(hdesk)
        except Exception:
            pass

        # Resolve foreground window once — shared by both focus and coverage checks
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        fg_is_desktop = True
        fg_on_target = False
        fg_hmon = None
        if hwnd:
            class_name = ctypes.create_string_buffer(256)
            ctypes.windll.user32.GetClassNameA(hwnd, class_name, 256)
            fg_class = class_name.value.decode("utf-8", errors="ignore")
            fg_is_desktop = (fg_class in IGNORED_CLASSES)
            fg_hmon = ctypes.windll.user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
            fg_on_target = any(m["hmonitor"] == fg_hmon for m in eval_monitors)

        # Focus check: if focus pause is enabled and an application is focused on target display
        if is_focus_pause and not fg_is_desktop and fg_on_target:
            return True

        algorithm = rules.get("algorithm", 3)

        # Algorithm 0: Foreground Process
        if algorithm == 0:
            if fg_is_desktop or not fg_on_target:
                return False
            if ctypes.windll.user32.IsZoomed(hwnd):
                return True
            rect = RECT()
            if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                target_work = next((m["work"] for m in eval_monitors if m["hmonitor"] == fg_hmon), None)
                if target_work and is_rect_covering(
                    (rect.left, rect.top, rect.right, rect.bottom), target_work, 0.95
                ):
                    return True
            return False

        # Algorithm 1: All Processes
        elif algorithm == 1:
            for m in eval_monitors:
                win_rects = get_visible_windows(target_monitor_rect=m["rect"])
                for r in win_rects:
                    if is_rect_covering(r, m["work"], 0.95):
                        return True
            return False

        # Algorithm 2: Direct3D Game Mode
        elif algorithm == 2:
            try:
                state = wintypes.DWORD()
                if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state)) == 0:
                    # QUNS_RUNNING_D3D_FULL_SCREEN = 2
                    if state.value == 2:
                        return True
            except Exception:
                pass
            return False

        # Algorithm 3: Grid (default)
        else:
            tile_size = rules.get("tile_size", 50)
            coverage_threshold = rules.get("coverage_threshold", 0.05)
            for m in eval_monitors:
                win_entries = get_visible_windows(target_monitor_rect=m["rect"], include_hwnds=True)
                win_rects = [r for r, _ in win_entries]
                win_hwnds = [h for _, h in win_entries]
                if is_grid_covered(m["work"], win_rects, tile_size=tile_size,
                                   coverage_threshold=coverage_threshold, hwnds=win_hwnds):
                    return True
            return False

    except Exception:
        return is_user_gaming_or_focused()

