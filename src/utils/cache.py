import os
from src.config import WALLPAPER_DIR, THUMBS_DIR, config, save_config
from src.utils.logger import log

def get_valid_wallpapers() -> set[str]:
    """Returns the set of existing video files currently present in the wallpapers directory."""
    if not os.path.exists(WALLPAPER_DIR):
        return set()
    return set(
        f for f in os.listdir(WALLPAPER_DIR)
        if f.lower().endswith((".mp4", ".webm", ".mkv"))
    )

def scan_orphans() -> dict[str, list[str]]:
    """
    Scans for cached items associated with wallpaper files that no longer exist on disk.
    Strictly read-only: does not modify or delete anything.
    
    Returns:
        {
            "orphan_thumbs": [list of orphan thumbnail file paths],
            "orphan_cache": [list of video filenames in duration_cache that no longer exist]
        }
    """
    valid_files = get_valid_wallpapers()
    orphan_thumbs: list[str] = []
    orphan_cache: list[str] = []

    # Check thumbnails folder
    if os.path.exists(THUMBS_DIR):
        for f in os.listdir(THUMBS_DIR):
            if f.lower().endswith(".jpg"):
                # Thumbnails are named as <video_filename>.jpg
                base_video_name = f[:-4]
                if base_video_name not in valid_files:
                    orphan_thumbs.append(os.path.join(THUMBS_DIR, f))

    # Check duration_cache in config
    duration_cache = config.get("duration_cache", {})
    for filename in duration_cache.keys():
        if filename not in valid_files:
            orphan_cache.append(filename)

    return {
        "orphan_thumbs": orphan_thumbs,
        "orphan_cache": orphan_cache
    }

def cleanup_orphans() -> dict[str, int]:
    """
    Safely removes orphan thumbnails and duration cache entries.
    Guarantees that no valid wallpapers in wallpapers/ or items in Library/ are touched.
    
    Returns:
        {"cleaned_thumbs": count, "cleaned_cache": count}
    """
    orphans = scan_orphans()
    orphan_thumbs = orphans["orphan_thumbs"]
    orphan_cache = orphans["orphan_cache"]

    cleaned_thumbs = 0
    cleaned_cache = 0

    # Delete orphan thumbs
    for thumb_path in orphan_thumbs:
        try:
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
                cleaned_thumbs += 1
        except Exception as e:
            log(f"Error removing orphan thumbnail {thumb_path}: {e}")

    # Remove orphan duration cache entries
    if orphan_cache:
        duration_cache = config.get("duration_cache", {})
        for key in orphan_cache:
            if key in duration_cache:
                del duration_cache[key]
                cleaned_cache += 1
        config["duration_cache"] = duration_cache
        save_config(config)

    log(f"Cache cleanup completed: removed {cleaned_thumbs} orphan thumbnails and {cleaned_cache} duration cache entries.")
    return {
        "cleaned_thumbs": cleaned_thumbs,
        "cleaned_cache": cleaned_cache
    }
