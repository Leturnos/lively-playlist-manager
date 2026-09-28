import os
import threading
import tkinter as tk
from tkinter import colorchooser
import pystray
from PIL import Image, ImageDraw
from src import state
from src.config import config, save_config, SOLID_COLOR_PRESETS
from src.utils.logger import log
from src.utils.solid_color import apply_solid_background

tray_icon = None
_picker_lock = threading.Lock()
_is_picker_open = False

def create_tray_icon_image():
    """Generates a procedural icon for the system tray."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Circle background
    d.ellipse([2, 2, 62, 62], fill=(30, 30, 40), outline=(120, 80, 200), width=3)
    # Play triangle
    d.polygon([(22, 18), (22, 46), (48, 32)], fill=(180, 120, 255))
    return img

def set_mode(mode: str):
    """Updates the rotation mode and dynamically adjusts the active limit without skipping."""
    config["mode"] = mode
    save_config(config)
    log(f"Mode changed to: {mode}")
    update_menu()

def set_rotation_order(order: str):
    """Updates the rotation order (shuffle vs sequential) and notifies the engine."""
    config["rotation_order"] = order
    save_config(config)
    log(f"Rotation order changed to: {order}")
    update_menu()
    state.playlist_needs_reload = True
    state.skip_event.set()

def set_playlist(playlist_name: str):
    """Updates the active sublist and notifies the engine."""
    if playlist_name == "Todos os Wallpapers":
        config["current_playlist"] = "All Wallpapers"
    else:
        config["current_playlist"] = playlist_name
    save_config(config)
    log(f"Active sublist changed to: {playlist_name}")
    update_menu()
    state.playlist_needs_reload = True
    state.skip_event.set()

def toggle_pause():
    """Toggles the global pause state."""
    state.is_paused = not state.is_paused
    status = "paused" if state.is_paused else "resumed"
    log(f"Rotation {status}")
    update_menu()

def skip_next():
    """Triggers the engine to move to the next wallpaper."""
    log("Skipping to next wallpaper (manual)")
    state.skip_event.set()

def play_previous():
    """Triggers the engine to play the previous wallpaper in history."""
    if state.history:
        log("Navigating to previous wallpaper")
        state.play_previous_event.set()
        state.skip_event.set()
    else:
        log("No wallpaper history to go back to")

def set_target_monitor(mon: str | int):
    """Updates the target monitor setting and notifies the engine."""
    config["target_monitor"] = mon
    save_config(config)
    log(f"Target monitor changed to: {mon}")
    update_menu()
    state.skip_event.set()

def set_solid_color(hex_val: str):
    """Updates the solid background color, applies it, and updates the tray menu."""
    apply_solid_background(hex_val)
    log(f"Solid background color changed to: {hex_val}")
    update_menu()

def pick_custom_solid_color():
    """Opens a native color chooser dialog in a background thread to pick a custom hex color."""
    global _is_picker_open
    with _picker_lock:
        if _is_picker_open:
            return
        _is_picker_open = True

    def _picker_worker():
        global _is_picker_open
        picker_root = None
        try:
            picker_root = tk.Tk()
            picker_root.withdraw()
            picker_root.attributes("-topmost", True)

            initial = config.get("solid_background_color", "#18181b")
            color = colorchooser.askcolor(color=initial, title="Escolher Cor de Fundo Sólida", parent=picker_root)

            if color and color[1]:
                set_solid_color(color[1].lower())
        except Exception as e:
            log(f"Error in custom color picker: {e}")
        finally:
            if picker_root is not None:
                try:
                    picker_root.destroy()
                except Exception:
                    pass
            with _picker_lock:
                _is_picker_open = False

    threading.Thread(target=_picker_worker, daemon=True, name="CustomColorPickerWorker").start()

def toggle_sync_lockscreen():
    """Toggles the lockscreen synchronization feature.

    Enabling is gated on a registry permission check: if the process cannot
    write to PersonalizationCSP, the toggle stays off and the user is notified
    to run setup_lockscreen_permission.bat as Administrator.
    The checkmark therefore only appears after permissions are confirmed.
    """
    from src.utils.lockscreen import (
        restore_lockscreen_registry,
        sync_lockscreen_worker,
        check_lockscreen_permissions,
    )
    from src.config import WALLPAPER_DIR

    currently_enabled = config.get("sync_lockscreen", False)

    if not currently_enabled:
        # Enabling: gate on registry write permission
        if not check_lockscreen_permissions():
            log("Lockscreen: permission denied. Run setup_lockscreen_permission.bat as Admin.")
            if tray_icon:
                try:
                    tray_icon.notify(
                        "Execute setup_lockscreen_permission.bat como Administrador para ativar as alterações.",
                        "Tela de Bloqueio",
                    )
                except Exception:
                    pass
            # Permission not granted: abort without changing config
            return

        config["sync_lockscreen"] = True
        save_config(config)
        log("Lockscreen synchronization enabled")

        if state.current_video:
            video_path = os.path.join(WALLPAPER_DIR, state.current_video)
            if os.path.exists(video_path):
                threading.Thread(
                    target=sync_lockscreen_worker,
                    args=(video_path,),
                    daemon=True,
                    name="LockscreenManualSyncWorker",
                ).start()
    else:
        # Disabling always works unconditionally
        config["sync_lockscreen"] = False
        save_config(config)
        log("Lockscreen synchronization disabled")
        restore_lockscreen_registry()

    update_menu()

def quit_app():
    """Signals all threads to stop and shuts down the tray icon."""
    state.stop_event.set()
    if state.hotkey_thread_id:
        try:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(state.hotkey_thread_id, 0x0012, 0, 0)
        except Exception:
            pass
    if tray_icon:
        tray_icon.stop()

def open_manager():
    """Opens the Tkinter Playlist Manager window in a separate thread."""
    from .manager import open_playlist_manager
    threading.Thread(target=open_playlist_manager, daemon=True).start()

def build_menu():
    """Constructs the system tray context menu."""
    from src.lively import get_lively_monitors

    def make_playlist_setter(p):
        return lambda: set_playlist(p)

    playlists = config.get("playlists", {})
    playlist_items = [
        pystray.MenuItem(
            "Todos os Wallpapers",
            make_playlist_setter("Todos os Wallpapers"),
            checked=lambda item: config.get("current_playlist", "All Wallpapers") in ("All Wallpapers", "Todos os Wallpapers"),
        )
    ]
    for pl_name in playlists.keys():
        playlist_items.append(
            pystray.MenuItem(
                pl_name,
                make_playlist_setter(pl_name),
                checked=(lambda p=pl_name: lambda item: config.get("current_playlist") == p)(),
            )
        )

    # Monitor menu items
    curr_mon = config.get("target_monitor")
    is_auto = (curr_mon in (None, "auto"))

    monitor_items = [
        pystray.MenuItem(
            "Seguir Lively (Auto)",
            lambda: set_target_monitor("auto"),
            checked=lambda item: config.get("target_monitor") in (None, "auto"),
        )
    ]
    for mon in get_lively_monitors():
        idx = mon["index"]
        name = mon["name"]
        primary_suffix = " (Principal)" if mon.get("is_primary") else ""
        label = f"Monitor {idx}: {name}{primary_suffix}"
        monitor_items.append(
            pystray.MenuItem(
                label,
                (lambda i=idx: lambda: set_target_monitor(i))(),
                checked=(lambda i=idx: lambda item: config.get("target_monitor") not in (None, "auto") and str(config.get("target_monitor")) == str(i))(),
            )
        )

    # Solid background color menu items
    curr_color = str(config.get("solid_background_color", "#18181b")).lower()
    is_disabled = (curr_color == "disabled")

    def make_color_setter(hex_val):
        return lambda: set_solid_color(hex_val)

    color_items = []
    color_items.append(
        pystray.MenuItem(
            "Desativada (Padrão do Windows)",
            lambda: set_solid_color("disabled"),
            checked=lambda item: str(config.get("solid_background_color", "#18181b")).lower() == "disabled",
        )
    )
    color_items.append(pystray.Menu.SEPARATOR)

    preset_hexes = set()
    for label, hex_val in SOLID_COLOR_PRESETS:
        h_lower = hex_val.lower()
        preset_hexes.add(h_lower)
        color_items.append(
            pystray.MenuItem(
                f"{label} ({hex_val})",
                make_color_setter(hex_val),
                checked=(lambda h=h_lower: lambda item: str(config.get("solid_background_color", "#18181b")).lower() == h)(),
            )
        )

    color_items.append(pystray.Menu.SEPARATOR)
    is_custom = (not is_disabled and curr_color not in preset_hexes)
    custom_label = f"Personalizada... ({curr_color})" if is_custom else "Personalizada..."
    color_items.append(
        pystray.MenuItem(
            custom_label,
            pick_custom_solid_color,
            checked=lambda item: (
                str(config.get("solid_background_color", "#18181b")).lower() != "disabled"
                and str(config.get("solid_background_color", "#18181b")).lower() not in {h.lower() for _, h in SOLID_COLOR_PRESETS}
            ),
        )
    )

    pause_label = "▶  Retomar Troca" if state.is_paused else "⏸  Pausar Troca"
    has_history = len(state.history) > 0

    return pystray.Menu(
        pystray.MenuItem("📋  Gerenciar Playlist", open_manager, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sublista Ativa", pystray.Menu(*playlist_items)),
        pystray.MenuItem("Tempo de Troca", pystray.Menu(
            pystray.MenuItem("Duração do Vídeo", lambda: set_mode("video"), checked=lambda item: config.get("mode") == "video"),
            pystray.MenuItem("30 segundos", lambda: set_mode("30s"), checked=lambda item: config.get("mode") == "30s"),
            pystray.MenuItem("1 minuto", lambda: set_mode("1min"), checked=lambda item: config.get("mode") == "1min"),
            pystray.MenuItem("5 minutos", lambda: set_mode("5min"), checked=lambda item: config.get("mode") == "5min"),
            pystray.MenuItem("10 minutos", lambda: set_mode("10min"), checked=lambda item: config.get("mode") == "10min"),
            pystray.MenuItem("30 minutos", lambda: set_mode("30min"), checked=lambda item: config.get("mode") == "30min"),
            pystray.MenuItem("1 hora", lambda: set_mode("1h"), checked=lambda item: config.get("mode") == "1h"),
        )),
        pystray.MenuItem("Modo de Rotação", pystray.Menu(
            pystray.MenuItem("Aleatório (Shuffle)", lambda: set_rotation_order("shuffle"), checked=lambda item: config.get("rotation_order", "shuffle") == "shuffle"),
            pystray.MenuItem("Sequencial", lambda: set_rotation_order("sequential"), checked=lambda item: config.get("rotation_order", "shuffle") == "sequential"),
        )),
        pystray.MenuItem("Monitor", pystray.Menu(*monitor_items)),
        pystray.MenuItem("Cor de Fundo Sólida", pystray.Menu(*color_items)),
        pystray.MenuItem(
            "Sincronizar Tela de Bloqueio",
            toggle_sync_lockscreen,
            checked=lambda item: config.get("sync_lockscreen", False),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(pause_label, toggle_pause),
        pystray.MenuItem("⏮  Voltar Anterior (Win+Alt+PgUp)", play_previous, enabled=has_history),
        pystray.MenuItem("⏭  Próximo Agora (Win+Alt+PgDn)", skip_next),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sair", quit_app),
    )

def update_menu():
    """Refreshes the tray icon menu to reflect state changes."""
    if tray_icon:
        tray_icon.menu = build_menu()

def start_tray():
    """Initializes and runs the system tray icon."""
    global tray_icon
    tray_icon = pystray.Icon(
        "wallpaper_playlist", 
        create_tray_icon_image(),
        "Wallpaper Playlist",
    )
    
    def setup(icon):
        icon.visible = True
        icon.menu = build_menu()

    tray_icon.run(setup=setup)
