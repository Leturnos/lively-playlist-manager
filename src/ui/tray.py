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
    """Placeholder: this will be linked to the Tkinter Manager window."""
    # This needs to be imported here or passed as a callback to avoid circular imports
    from .manager import open_playlist_manager
    threading.Thread(target=open_playlist_manager, daemon=True).start()

def build_menu():
    """Constructs the system tray context menu."""
    m = config.get("mode")
    def get_check(mode_key): return "✓ " if m == mode_key else "   "
    
    order = config.get("rotation_order", "shuffle")
    def get_order_check(o_key): return "✓ " if order == o_key else "   "
    
    current_pl = config.get("current_playlist", "All Wallpapers")
    if current_pl == "All Wallpapers":
        current_pl_ui = "Todos os Wallpapers"
    else:
        current_pl_ui = current_pl
    def get_playlist_check(pl_key): return "✓ " if current_pl_ui == pl_key else "   "
    
    def make_playlist_setter(p):
        return lambda: set_playlist(p)
        
    playlists = config.get("playlists", {})
    playlist_items = [
        pystray.MenuItem(f"{get_playlist_check('Todos os Wallpapers')}Todos os Wallpapers", make_playlist_setter("Todos os Wallpapers"))
    ]
    for pl_name in playlists.keys():
        playlist_items.append(
            pystray.MenuItem(f"{get_playlist_check(pl_name)}{pl_name}", make_playlist_setter(pl_name))
        )
    
    pause_label = "▶  Retomar Troca" if state.is_paused else "⏸  Pausar Troca"
    has_history = len(state.history) > 0
    
    return pystray.Menu(
        # Hidden default action for double-click/single-click on the icon
        pystray.MenuItem("Abrir Gerenciador", open_manager, default=True, visible=False),
        pystray.MenuItem("🎞  Wallpaper Playlist", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sublista Ativa", pystray.Menu(*playlist_items)),
        pystray.MenuItem("Tempo de Troca", pystray.Menu(
            pystray.MenuItem(f"{get_check('video')}Duração do Vídeo", lambda: set_mode("video")),
            pystray.MenuItem(f"{get_check('30s')}30 segundos", lambda: set_mode("30s")),
            pystray.MenuItem(f"{get_check('1min')}1 minuto", lambda: set_mode("1min")),
            pystray.MenuItem(f"{get_check('5min')}5 minutos", lambda: set_mode("5min")),
            pystray.MenuItem(f"{get_check('10min')}10 minutos", lambda: set_mode("10min")),
            pystray.MenuItem(f"{get_check('30min')}30 minutos", lambda: set_mode("30min")),
            pystray.MenuItem(f"{get_check('1h')}1 hora", lambda: set_mode("1h")),
        )),
        pystray.MenuItem("Modo de Rotação", pystray.Menu(
            pystray.MenuItem(f"{get_order_check('shuffle')}Aleatório (Shuffle)", lambda: set_rotation_order("shuffle")),
            pystray.MenuItem(f"{get_order_check('sequential')}Sequencial", lambda: set_rotation_order("sequential"))
        )),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(pause_label, toggle_pause),
        pystray.MenuItem("⏮  Voltar Anterior (Win+Alt+PgUp)", play_previous, enabled=has_history),
        pystray.MenuItem("⏭  Próximo Agora (Win+Alt+PgDn)", skip_next),
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
