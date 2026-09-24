import os
from PIL import Image, ImageDraw
from moviepy import VideoFileClip
from src.config import WALLPAPER_DIR, THUMBS_DIR, LOCKSCREEN_FRAMES_DIR
from src.state import thumbs_ready, thumbs_lock, stop_event
from src.utils.logger import log

THUMB_W, THUMB_H = 200, 113

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

        # Opportunistically pre-cache full-resolution frame for lockscreen
        if not os.path.exists(cached_frame):
            os.makedirs(LOCKSCREEN_FRAMES_DIR, exist_ok=True)
            img.save(cached_frame, "JPEG", quality=95)

        thumb_img = img.resize((THUMB_W, THUMB_H), Image.Resampling.LANCZOS)
        os.makedirs(THUMBS_DIR, exist_ok=True)
        thumb_img.save(thumb_path, "JPEG", quality=85)
        
        with thumbs_lock:
            thumbs_ready[filename] = thumb_path
    except Exception as e:
        log(f"Thumbnail generation failed for {filename}: {e}")

def background_thumbnail_generator():
    """Worker thread to generate thumbnails for all videos in the wallpaper directory."""
    files = sorted([
        f for f in os.listdir(WALLPAPER_DIR)
        if f.lower().endswith((".mp4", ".webm", ".mkv"))
    ])
    
    for filename in files:
        if stop_event.is_set():
            break
        generate_thumbnail(filename)
