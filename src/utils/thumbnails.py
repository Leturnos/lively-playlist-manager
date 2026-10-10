import os
import threading
from PIL import Image, ImageDraw
from moviepy import VideoFileClip
from src.config import WALLPAPER_DIR, THUMBS_DIR, LOCKSCREEN_FRAMES_DIR
from src.state import thumbs_ready, thumbs_lock, stop_event
from src.utils.logger import log

THUMB_W, THUMB_H = 200, 113

_thumb_thread: threading.Thread | None = None
_thumb_thread_lock = threading.Lock()

def create_placeholder():
    """Creates a placeholder image for videos without thumbnails yet."""
    img = Image.new("RGB", (THUMB_W, THUMB_H), (40, 40, 55))
    ImageDraw.Draw(img).rectangle([0, 0, THUMB_W-1, THUMB_H-1], outline=(80, 80, 100))
    return img

def generate_thumbnail(filename: str):
    """Extracts a frame from a video and saves it as a JPEG thumbnail, pre-caching high-res frame."""
    thumb_path = os.path.join(THUMBS_DIR, filename + ".jpg")
    cached_frame = os.path.join(LOCKSCREEN_FRAMES_DIR, filename + ".jpg")
    
    if os.path.exists(thumb_path) and os.path.exists(cached_frame):
        with thumbs_lock:
            thumbs_ready[filename] = thumb_path
        return

    video_path = os.path.join(WALLPAPER_DIR, filename)
    if not os.path.exists(video_path):
        return

    try:
        clip = VideoFileClip(video_path)
        # Get frame at 10% of duration (capped at 1.0s to avoid slow seeks on long videos)
        sample_time = min(1.0, clip.duration * 0.1) if clip.duration and clip.duration > 0 else 0
        frame = clip.get_frame(sample_time)
        clip.close()
        
        img = Image.fromarray(frame)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        # Opportunistically pre-cache frame for lockscreen (optimized for screen resolution)
        if not os.path.exists(cached_frame):
            os.makedirs(LOCKSCREEN_FRAMES_DIR, exist_ok=True)
            try:
                from src.utils.solid_color import get_screen_resolution
                screen_w, screen_h = get_screen_resolution()
                if img.width > screen_w or img.height > screen_h:
                    save_frame = img.copy()
                    save_frame.thumbnail((screen_w, screen_h), Image.Resampling.LANCZOS)
                else:
                    save_frame = img
            except Exception:
                save_frame = img
            save_frame.save(cached_frame, "JPEG", quality=90, progressive=False)

        thumb_img = img.resize((THUMB_W, THUMB_H), Image.Resampling.LANCZOS)
        os.makedirs(THUMBS_DIR, exist_ok=True)
        thumb_img.save(thumb_path, "JPEG", quality=85)
        
        with thumbs_lock:
            thumbs_ready[filename] = thumb_path
    except Exception as e:
        log(f"Thumbnail generation failed for {filename}: {e}")

def background_thumbnail_generator():
    """Worker thread to generate thumbnails for all videos in the wallpaper directory."""
    if not os.path.exists(WALLPAPER_DIR):
        return

    files = sorted([
        f for f in os.listdir(WALLPAPER_DIR)
        if f.lower().endswith((".mp4", ".webm", ".mkv"))
    ])
    
    for filename in files:
        if stop_event.is_set():
            break
        generate_thumbnail(filename)

def start_thumbnail_generator() -> threading.Thread | None:
    """
    Starts or restarts the thumbnail generation worker thread if not already running.
    Scans the wallpaper directory and generates thumbnails / high-res frame caches
    for any missing files.
    """
    global _thumb_thread
    with _thumb_thread_lock:
        if _thumb_thread is not None and _thumb_thread.is_alive():
            return _thumb_thread

        _thumb_thread = threading.Thread(
            target=background_thumbnail_generator,
            daemon=True,
            name="ThumbnailGeneratorWorker"
        )
        _thumb_thread.start()
        return _thumb_thread
