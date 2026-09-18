import os
import random
import time
import threading
from moviepy import VideoFileClip
from src.config import config, WALLPAPER_DIR, load_config, save_config
from src.utils.logger import log
from src.utils.window_state import is_user_gaming_or_focused
from src.lively import set_wallpaper
from src.utils.lockscreen import sync_lockscreen_worker
from src import state

def get_video_duration(video_path: str) -> float | None:
    """Gets the duration of a video in seconds, caching the result in config."""
    filename = os.path.basename(video_path)
    cache = config.get("duration_cache", {})
    if filename in cache:
        return cache[filename]
        
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
        
        # Save to cache
        cache[filename] = duration
        config["duration_cache"] = cache
        save_config(config)
        
        return duration
    except Exception as e:
        log(f"ERROR getting duration for {video_path}: {e}")
        return None

def get_playlist() -> list[str]:
    """Retrieves the list of active wallpaper paths, reloading config from disk."""
    # Refresh config to pick up changes from the UI manager
    current_config = load_config()
    config.update(current_config)
    
    all_files = sorted([
        f for f in os.listdir(WALLPAPER_DIR)
        if f.lower().endswith((".mp4", ".webm", ".mkv"))
    ])
    
    current_playlist_name = config.get("current_playlist", "All Wallpapers")
    
    if current_playlist_name == "All Wallpapers":
        active_list = config.get("active_wallpapers", [])
    else:
        playlists = config.get("playlists", {})
        active_list = playlists.get(current_playlist_name, [])
        
    selected = [f for f in all_files if not active_list or f in active_list]
    
    return [os.path.join(WALLPAPER_DIR, f) for f in (selected or all_files)]

def run_rotation_engine():
    """Main loop that manages the wallpaper rotation based on the chosen mode."""
    log(f"Starting rotation engine. Directory: {WALLPAPER_DIR}")
    os.makedirs(WALLPAPER_DIR, exist_ok=True)

    is_first_cycle = True

    while not state.stop_event.is_set():
        try:
            if config.get("mode") is None:
                time.sleep(2)
                continue

            playlist = get_playlist()
            if not playlist:
                time.sleep(10)
                continue

            order = config.get("rotation_order", "shuffle")
            last_played = config.get("last_played_wallpaper")

            # Validate last_played defensively
            has_valid_last_played = isinstance(last_played, str) and bool(last_played.strip())

            matched_index = None
            if has_valid_last_played:
                for idx, p in enumerate(playlist):
                    if os.path.basename(p).lower() == last_played.lower():
                        matched_index = idx
                        break

            if order == "shuffle":
                if is_first_cycle and matched_index is not None:
                    # Initial boot: pin last played wallpaper to index 0 to match lock screen
                    remaining = [p for i, p in enumerate(playlist) if i != matched_index]
                    random.shuffle(remaining)
                    playlist = [playlist[matched_index]] + remaining
                else:
                    random.shuffle(playlist)
                    # Anti-repeat guard across shuffle cycle boundaries
                    if (
                        len(playlist) > 1
                        and has_valid_last_played
                        and os.path.basename(playlist[0]).lower() == last_played.lower()
                    ):
                        swap_idx = random.randint(1, len(playlist) - 1)
                        playlist[0], playlist[swap_idx] = playlist[swap_idx], playlist[0]
            else:
                # Sequential mode
                if matched_index is not None:
                    if is_first_cycle:
                        # Initial boot: start with last played wallpaper to match lock screen
                        start_index = matched_index
                    else:
                        # Subsequent cycles / reloads: advance to the next wallpaper in sequence
                        start_index = (matched_index + 1) % len(playlist)
                    playlist = playlist[start_index:] + playlist[:start_index]

            is_first_cycle = False

            log(f"Playlist initialized: {len(playlist)} videos. Mode: {config['mode']}")

            for video_path in playlist:
                if state.stop_event.is_set():
                    break

                if state.playlist_needs_reload:
                    state.playlist_needs_reload = False
                    break

                # Handle "Play Previous" request
                if state.play_previous_event.is_set():
                    state.play_previous_event.clear()
                    if state.history:
                        state.is_going_back = True
                        video_path = state.history.pop()

                # Handle "Play Now" request from Manager
                elif state.play_specific_event.is_set():
                    state.play_specific_event.clear()
                    if state.next_video_request:
                        video_path = state.next_video_request
                        state.next_video_request = None

                duration = get_video_duration(video_path)
                if duration is None:
                    continue

                log(f"Next wallpaper: {os.path.basename(video_path)} ({duration:.1f}s)")

                if not set_wallpaper(video_path):
                    time.sleep(5)
                    continue

                # Persist the active wallpaper to resume from where it left off on next startup
                current_basename = os.path.basename(video_path)
                if config.get("last_played_wallpaper") != current_basename:
                    config["last_played_wallpaper"] = current_basename
                    save_config(config)

                if config.get("sync_lockscreen", False):
                    threading.Thread(
                        target=sync_lockscreen_worker,
                        args=(video_path,),
                        daemon=True,
                        name="LockscreenSyncWorker"
                    ).start()

                try:
                    from src.ui.tray import update_menu
                    update_menu()
                except Exception:
                    pass

                mode = config.get("mode", "video")
                limit = {
                    "30s": 30,
                    "1min": 60,
                    "5min": 300,
                    "10min": 600,
                    "30min": 1800,
                    "1h": 3600
                }.get(mode, duration)
                effective_limit = max(1, limit - 1) if mode == "video" else limit

                state.skip_event.clear()
                active_time = 0.0
                last_tick = time.time()
                last_loop_log = 0
                
                while True:
                    if (state.stop_event.is_set() or 
                        state.skip_event.is_set() or 
                        state.play_specific_event.is_set() or 
                        state.play_previous_event.is_set() or
                        state.playlist_needs_reload):
                        break
                    if active_time >= effective_limit:
                        break

                    now = time.time()
                    delta = now - last_tick
                    last_tick = now

                    if state.is_paused:
                        time.sleep(1)
                        continue
                        
                    if is_user_gaming_or_focused():
                        # Desktop is likely covered by a fullscreen app; don't count this time
                        time.sleep(1)
                        continue

                    active_time += delta
                    time.sleep(0.5)

                    # Log when a video loops (if rotation limit > duration)
                    if int(duration) > 0:
                        current_cycle = int(active_time / duration)
                        if current_cycle > last_loop_log and active_time < effective_limit:
                            last_loop_log = current_cycle
                            log(f"Looping: {os.path.basename(video_path)}")

        except Exception as e:
            log(f"Rotation engine error: {e}")
            time.sleep(2)

    log("Rotation engine stopped.")
