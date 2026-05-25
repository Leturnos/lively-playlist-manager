import os
from PIL import Image, ImageDraw
from moviepy import VideoFileClip
from src.config import WALLPAPER_DIR, THUMBS_DIR
from src.state import thumbs_ready, thumbs_lock, stop_event
from src.utils.logger import log

THUMB_W, THUMB_H = 200, 113

def create_placeholder():
    """Creates a placeholder image for videos without thumbnails yet."""
    img = Image.new("RGB", (THUMB_W, THUMB_H), (40, 40, 55))
    ImageDraw.Draw(img).rectangle([0, 0, THUMB_W-1, THUMB_H-1], outline=(80, 80, 100))
    return img

def generate_thumbnail(filename: str):
    """Extracts a frame from a video and saves it as a JPEG thumbnail."""
    thumb_path = os.path.join(THUMBS_DIR, filename + ".jpg")
    
    if os.path.exists(thumb_path):
        with thumbs_lock:
            thumbs_ready[filename] = thumb_path
        return

    video_path = os.path.join(WALLPAPER_DIR, filename)
    if not os.path.exists(video_path):
        return

    try:
        clip = VideoFileClip(video_path)
        # Get frame at 10% of duration
        frame = clip.get_frame(min(1.0, clip.duration * 0.1))
        clip.close()
        
        img = Image.fromarray(frame).resize((THUMB_W, THUMB_H), Image.Resampling.LANCZOS)
        os.makedirs(THUMBS_DIR, exist_ok=True)
        img.save(thumb_path, "JPEG", quality=85)
        
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
