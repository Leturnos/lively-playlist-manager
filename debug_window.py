import ctypes
import time

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

print("Mostrando foreground window a cada 2s. Deixe a área de trabalho em foco.")
print("Ctrl+C para parar.\n")

for _ in range(20):
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    
    class_name = ctypes.create_string_buffer(255)
    ctypes.windll.user32.GetClassNameA(hwnd, class_name, 255)
    
    win_title = ctypes.create_unicode_buffer(255)
    ctypes.windll.user32.GetWindowTextW(hwnd, win_title, 255)
    
    rect = RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    
    sw = ctypes.windll.user32.GetSystemMetrics(0)
    sh = ctypes.windll.user32.GetSystemMetrics(1)
    
    print(f"hwnd={hwnd} | class='{class_name.value.decode('utf-8', errors='ignore')}' | title='{win_title.value}' | {w}x{h} (tela={sw}x{sh})")
    time.sleep(2)
