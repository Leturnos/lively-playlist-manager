import os
import random
import time
from moviepy import VideoFileClip
from src.config import config, WALLPAPER_DIR, load_config
from src.utils.logger import log
from src.utils.window_state import is_user_gaming_or_focused
from src.lively import set_wallpaper
from src import state

def get_video_duration(video_path: str) -> float | None:
    """Gets the duration of a video in seconds."""
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        clip.close()
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
    
    active_list = config.get("active_wallpapers", [])
    selected = [f for f in all_files if not active_list or f in active_list]
    
    return [os.path.join(WALLPAPER_DIR, f) for f in (selected or all_files)]

def run_rotation_engine():
    """Main loop that manages the wallpaper rotation based on the chosen mode."""
    log(f"Starting rotation engine. Directory: {WALLPAPER_DIR}")
    os.makedirs(WALLPAPER_DIR, exist_ok=True)

    while not state.stop_event.is_set():
        if config.get("mode") is None:
            time.sleep(2)
            continue

        playlist = get_playlist()
        random.shuffle(playlist)

        if not playlist:
            time.sleep(10)
            continue

        log(f"Playlist initialized: {len(playlist)} videos. Mode: {config['mode']}")

        for video_path in playlist:
            if state.stop_event.is_set():
                break

            # Handle "Play Now" request from Manager
            if state.play_specific_event.is_set():
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

            mode = config.get("mode", "video")
            limit = {"1min": 60, "5min": 300}.get(mode, duration)
            effective_limit = max(1, limit - 1) if mode == "video" else limit

            state.skip_event.clear()
            active_time = 0.0
            last_tick = time.time()
            last_loop_log = 0
            
            while True:
                if state.stop_event.is_set() or state.skip_event.is_set() or state.play_specific_event.is_set():
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

    log("Rotation engine stopped.")
