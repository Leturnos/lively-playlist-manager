import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from src.config import config, save_config, WALLPAPER_DIR
from src.utils.logger import log
from src.utils.thumbnails import THUMB_W, THUMB_H, create_placeholder
from src.ui.theme import COLORS
from src import state

COLS = 3

def clean_name(filename: str) -> str:
    """Removes common suffixes and extensions for a cleaner UI display."""
    return (filename
            .replace("-moewalls-com", "")
            .replace("-", " ")
            .split(".")[0])

def open_playlist_manager():
    """Opens the Tkinter-based playlist management window."""
    if state.is_window_open:
        return
    state.is_window_open = True

    all_files = sorted([
        f for f in os.listdir(WALLPAPER_DIR)
        if f.lower().endswith((".mp4", ".webm", ".mkv"))
    ])
    
    saved_active = config.get("active_wallpapers", [])
    checks = {}
    tk_images = {}
    image_labels = {}
    cards_map = {}

    root = tk.Tk()
    root.title("Wallpaper Playlist Manager")
    root.geometry("740x700")
    root.configure(bg=COLORS["base"])
    root.resizable(True, True)
    
    # Bring to front initially
    root.lift()
    root.attributes("-topmost", True)
    root.after(200, lambda: root.attributes("-topmost", False))

    def on_close():
        state.is_window_open = False
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)

    for name in all_files:
        checks[name] = tk.BooleanVar(value=(not saved_active or name in saved_active))

    # --- Search & Filter ---
    filter_var = tk.StringVar(value="all")
    search_var = tk.StringVar()

    def get_filtered_list():
        term = search_var.get().lower()
        mode = filter_var.get()
        result = []
        for n in all_files:
            if term and term not in clean_name(n).lower():
                continue
            is_active = checks[n].get()
            if mode == "active" and not is_active: continue
            if mode == "inactive" and is_active: continue
            result.append(n)
        return result

    # --- Header ---
    header = tk.Frame(root, bg=COLORS["base"])
    header.pack(fill="x", padx=14, pady=(12, 6))

    tk.Label(header, text="🎞  Wallpaper Playlist", bg=COLORS["base"],
             fg=COLORS["mauve"], font=("Segoe UI", 13, "bold")).pack(side="left")

    counter_var = tk.StringVar()
    tk.Label(header, textvariable=counter_var, bg=COLORS["base"],
             fg=COLORS["muted"], font=("Segoe UI", 9)).pack(side="right", padx=(0, 4))

    # --- Toolbar ---
    toolbar = tk.Frame(root, bg=COLORS["base"])
    toolbar.pack(fill="x", padx=14, pady=(0, 6))

    tk.Label(toolbar, text="🔍", bg=COLORS["base"], fg=COLORS["subtext"]).pack(side="left")
    tk.Entry(toolbar, textvariable=search_var, bg=COLORS["surface"], fg=COLORS["text"],
             insertbackground=COLORS["text"], relief="flat",
             font=("Segoe UI", 10), bd=6).pack(side="left", fill="x", expand=True, padx=(4, 10))

    # Filter toggles
    filter_frame = tk.Frame(toolbar, bg=COLORS["base"])
    filter_frame.pack(side="left")

    btn_refs = {}
    def set_filter(f):
        filter_var.set(f)
        for k, b in btn_refs.items():
            active = (k == f)
            b.configure(
                bg=COLORS["mauve"] if active else COLORS["surface"],
                fg=COLORS["base"] if active else COLORS["text"]
            )
        redraw()

    for label, key in [("All", "all"), ("Active", "active"), ("Inactive", "inactive")]:
        b = tk.Button(filter_frame, text=label,
                      bg=COLORS["mauve"] if key == "all" else COLORS["surface"],
                      fg=COLORS["base"] if key == "all" else COLORS["text"],
                      relief="flat", font=("Segoe UI", 9), padx=10, pady=3,
                      cursor="hand2", activebackground=COLORS["overlay"],
                      activeforeground=COLORS["text"],
                      command=lambda k=key: set_filter(k))
        b.pack(side="left", padx=(0, 2))
        btn_refs[key] = b

    sep = tk.Frame(toolbar, bg=COLORS["overlay"], width=1)
    sep.pack(side="left", fill="y", padx=8)

    def select_all():
        for n in get_filtered_list():
            checks[n].set(True)
        redraw()

    def deselect_all():
        for n in get_filtered_list():
            checks[n].set(False)
        redraw()

    tk.Button(toolbar, text="✓ Select All", command=select_all,
              bg=COLORS["surface"], fg=COLORS["text"], relief="flat",
              font=("Segoe UI", 9), padx=8, pady=3).pack(side="left", padx=(0, 2))
    tk.Button(toolbar, text="✗ Deselect All", command=deselect_all,
              bg=COLORS["surface"], fg=COLORS["text"], relief="flat",
              font=("Segoe UI", 9), padx=8, pady=3).pack(side="left")

    # --- Grid ---
    container = tk.Frame(root, bg=COLORS["base"])
    container.pack(fill="both", expand=True, padx=14, pady=4)

    canvas = tk.Canvas(container, bg=COLORS["mantle"], highlightthickness=0)
    sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    grid_frame = tk.Frame(canvas, bg=COLORS["mantle"])

    grid_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    cw = canvas.create_window((0, 0), window=grid_frame, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
    canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    placeholder_pil = create_placeholder()

    def update_counter():
        n_at = sum(v.get() for v in checks.values())
        counter_var.set(f"{n_at} of {len(checks)} active")

    def get_border_color(name):
        is_playing = (name == state.current_video)
        is_checked = checks[name].get()
        if is_playing: return COLORS["green"]
        if is_checked: return COLORS["mauve"]
        return COLORS["surface"]

    def create_cards(list_to_show):
        for w in grid_frame.winfo_children():
            w.destroy()
        cards_map.clear()
        image_labels.clear()

        for idx, name in enumerate(list_to_show):
            row, col = divmod(idx, COLS)
            var = checks[name]

            card = tk.Frame(grid_frame, bg=COLORS["mantle"], padx=3, pady=3,
                            highlightthickness=2,
                            highlightbackground=get_border_color(name))
            card.grid(row=row, column=col, padx=6, pady=6, sticky="n")
            cards_map[name] = card

            with state.thumbs_lock:
                tp = state.thumbs_ready.get(name)
            
            if tp and os.path.exists(tp):
                pil = Image.open(tp).resize((THUMB_W, THUMB_H), Image.Resampling.LANCZOS)
            else:
                pil = placeholder_pil.copy()
            
            tk_img = ImageTk.PhotoImage(pil)
            tk_images[name] = tk_img

            lbl = tk.Label(card, image=tk_img, bg=COLORS["mantle"], cursor="hand2")
            lbl.pack()
            image_labels[name] = lbl

            def _toggle(e, n=name, c=card):
                checks[n].set(not checks[n].get())
                c.configure(highlightbackground=get_border_color(n))
                update_counter()
            lbl.bind("<Button-1>", _toggle)

            if name == state.current_video:
                tk.Label(card, text="▶ playing now", bg=COLORS["green"], fg=COLORS["base"],
                         font=("Segoe UI", 7, "bold"), padx=4).pack(fill="x")

            tk.Label(card, text=clean_name(name), bg=COLORS["mantle"], fg=COLORS["text"],
                     font=("Segoe UI", 8), wraplength=THUMB_W,
                     justify="center").pack(pady=(2, 0))

            bottom = tk.Frame(card, bg=COLORS["mantle"])
            bottom.pack(fill="x", pady=(2, 0))

            tk.Checkbutton(bottom, variable=var, bg=COLORS["mantle"],
                           selectcolor=COLORS["surface"], fg=COLORS["mauve"],
                           text="Active", font=("Segoe UI", 8),
                           command=lambda n=name, c=card: (
                               c.configure(highlightbackground=get_border_color(n)),
                               update_counter()
                           )).pack(side="left", padx=4)

            def play_now(n=name):
                state.next_video_request = os.path.join(WALLPAPER_DIR, n)
                state.play_specific_event.set()
                state.skip_event.set()
                log(f"Manual play requested: {n}")

            tk.Button(bottom, text="▶ Play", command=play_now,
                      bg=COLORS["surface"], fg=COLORS["mauve"], relief="flat",
                      font=("Segoe UI", 8), padx=6, pady=1,
                      cursor="hand2").pack(side="right", padx=4)

        update_counter()

    def redraw(*_):
        create_cards(get_filtered_list())

    search_var.trace_add("write", redraw)
    create_cards(all_files)

    def scroll_to_current():
        if state.current_video and state.current_video in cards_map:
            card = cards_map[state.current_video]
            root.update_idletasks()
            y = card.winfo_y()
            total = grid_frame.winfo_height()
            if total > 0:
                canvas.yview_moveto(max(0, (y - 100) / total))
    root.after(300, scroll_to_current)

    def check_new_thumbs():
        if not root.winfo_exists(): return
        with state.thumbs_lock:
            ready = dict(state.thumbs_ready)
        for name, path in ready.items():
            if name in image_labels and image_labels[name].winfo_exists():
                # Logic to update if it was a placeholder
                pass 
        root.after(2000, check_new_thumbs)
    root.after(2000, check_new_thumbs)

    def save_and_close():
        selected = [n for n, v in checks.items() if v.get()]
        config["active_wallpapers"] = [] if len(selected) == len(all_files) else selected
        save_config(config)
        log(f"Selection saved: {len(selected)} active")
        state.skip_event.set()
        on_close()

    footer = tk.Frame(root, bg=COLORS["base"])
    footer.pack(fill="x", padx=14, pady=(4, 12))

    tk.Button(footer, text="✔  Save and Close", command=save_and_close,
              bg=COLORS["mauve"], fg=COLORS["base"], relief="flat",
              font=("Segoe UI", 10, "bold"), pady=8,
              cursor="hand2").pack(fill="x")

    root.mainloop()
