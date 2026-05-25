import time

def log(message: str):
    """Prints a timestamped message to the console."""
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)
