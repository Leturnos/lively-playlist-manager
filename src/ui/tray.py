import threading
import pystray
from PIL import Image, ImageDraw
from src import state
from src.config import config, save_config
from src.utils.logger import log

tray_icon = None

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
    """Updates the rotation mode and notifies the engine."""
    config["mode"] = mode
    save_config(config)
    log(f"Mode changed to: {mode}")
    update_menu()
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

def quit_app():
    """Signals all threads to stop and shuts down the tray icon."""
    state.stop_event.set()
    if tray_icon:
        tray_icon.stop()

def open_manager():
    """Placeholder: this will be linked to the Tkinter Manager window."""
    # This needs to be imported here or passed as a callback to avoid circular imports
    from .manager import open_playlist_manager
    threading.Thread(target=open_playlist_manager, daemon=True).start()

def build_menu():
    """Constructs the system tray context menu."""
    m = config.get("mode")
    def get_check(mode_key): return "✓ " if m == mode_key else "   "
    
    pause_label = "▶  Retomar Troca" if state.is_paused else "⏸  Pausar Troca"
    
    return pystray.Menu(
        # Hidden default action for double-click/single-click on the icon
        pystray.MenuItem("Abrir Gerenciador", open_manager, default=True, visible=False),
        pystray.MenuItem("🎞  Wallpaper Playlist", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"{get_check('video')}Duração do Vídeo", lambda: set_mode("video")),
        pystray.MenuItem(f"{get_check('1min')}Trocar a cada 1 min", lambda: set_mode("1min")),
        pystray.MenuItem(f"{get_check('5min')}Trocar a cada 5 min", lambda: set_mode("5min")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(pause_label, toggle_pause),
        pystray.MenuItem("⏭  Próximo Agora", skip_next),
        pystray.MenuItem("📋  Gerenciar Playlist", open_manager),
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
