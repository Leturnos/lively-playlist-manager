import tkinter as tk
from src.ui.theme import COLORS

def _center_dialog(dialog: tk.Toplevel, parent: tk.Tk | tk.Toplevel, width: int = 380, height: int = 160):
    """Centers the dialog window over the parent window."""
    dialog.update_idletasks()
    parent_x = parent.winfo_rootx()
    parent_y = parent.winfo_rooty()
    parent_w = parent.winfo_width()
    parent_h = parent.winfo_height()
    
    x = parent_x + max(0, (parent_w - width) // 2)
    y = parent_y + max(0, (parent_h - height) // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

def prompt_dialog(parent: tk.Tk | tk.Toplevel, title: str, message: str, initial_value: str = "") -> str | None:
    """
    Displays a modal text input dialog styled with Catppuccin Mocha.
    Returns the entered string, or None if cancelled.
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.configure(bg=COLORS["base"])
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    result: list[str | None] = [None]

    content_frame = tk.Frame(dialog, bg=COLORS["base"], padx=18, pady=16)
    content_frame.pack(fill="both", expand=True)

    tk.Label(
        content_frame,
        text=message,
        bg=COLORS["base"],
        fg=COLORS["text"],
        font=("Segoe UI", 10),
        wraplength=340,
        justify="left"
    ).pack(anchor="w", pady=(0, 10))

    entry_var = tk.StringVar(value=initial_value)
    entry = tk.Entry(
        content_frame,
        textvariable=entry_var,
        bg=COLORS["surface"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        relief="flat",
        font=("Segoe UI", 10),
        bd=6
    )
    entry.pack(fill="x", pady=(0, 16))
    entry.focus_set()
    entry.select_range(0, tk.END)

    btn_frame = tk.Frame(content_frame, bg=COLORS["base"])
    btn_frame.pack(fill="x")

    def on_confirm():
        val = entry_var.get().strip()
        result[0] = val
        dialog.destroy()

    def on_cancel():
        result[0] = None
        dialog.destroy()

    btn_cancel = tk.Button(
        btn_frame,
        text="Cancelar",
        command=on_cancel,
        bg=COLORS["surface"],
        fg=COLORS["subtext"],
        relief="flat",
        font=("Segoe UI", 9),
        padx=12,
        pady=4,
        cursor="hand2"
    )
    btn_cancel.pack(side="right", padx=(6, 0))

    btn_ok = tk.Button(
        btn_frame,
        text="Confirmar",
        command=on_confirm,
        bg=COLORS["mauve"],
        fg=COLORS["base"],
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=14,
        pady=4,
        cursor="hand2"
    )
    btn_ok.pack(side="right")

    dialog.bind("<Return>", lambda e: on_confirm())
    dialog.bind("<Escape>", lambda e: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    _center_dialog(dialog, parent, 380, 170)
    dialog.wait_window()
    return result[0]

def confirm_dialog(parent: tk.Tk | tk.Toplevel, title: str, message: str, is_destructive: bool = False) -> bool:
    """
    Displays a modal confirmation dialog (Yes / No) styled with Catppuccin Mocha.
    Returns True if confirmed, False otherwise.
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.configure(bg=COLORS["base"])
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    confirmed = [False]

    content_frame = tk.Frame(dialog, bg=COLORS["base"], padx=18, pady=16)
    content_frame.pack(fill="both", expand=True)

    tk.Label(
        content_frame,
        text=message,
        bg=COLORS["base"],
        fg=COLORS["text"],
        font=("Segoe UI", 10),
        wraplength=340,
        justify="left"
    ).pack(anchor="w", pady=(0, 18))

    btn_frame = tk.Frame(content_frame, bg=COLORS["base"])
    btn_frame.pack(fill="x")

    def on_yes():
        confirmed[0] = True
        dialog.destroy()

    def on_no():
        confirmed[0] = False
        dialog.destroy()

    btn_cancel = tk.Button(
        btn_frame,
        text="Não",
        command=on_no,
        bg=COLORS["surface"],
        fg=COLORS["subtext"],
        relief="flat",
        font=("Segoe UI", 9),
        padx=16,
        pady=4,
        cursor="hand2"
    )
    btn_cancel.pack(side="right", padx=(6, 0))

    action_color = COLORS["red"] if is_destructive else COLORS["mauve"]
    btn_confirm = tk.Button(
        btn_frame,
        text="Sim",
        command=on_yes,
        bg=action_color,
        fg=COLORS["base"],
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=18,
        pady=4,
        cursor="hand2"
    )
    btn_confirm.pack(side="right")

    dialog.bind("<Return>", lambda e: on_yes())
    dialog.bind("<Escape>", lambda e: on_no())
    dialog.protocol("WM_DELETE_WINDOW", on_no)

    _center_dialog(dialog, parent, 380, 150)
    dialog.wait_window()
    return confirmed[0]

def info_dialog(parent: tk.Tk | tk.Toplevel, title: str, message: str, is_error: bool = False):
    """
    Displays a modal notification or error dialog styled with Catppuccin Mocha.
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.configure(bg=COLORS["base"])
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    content_frame = tk.Frame(dialog, bg=COLORS["base"], padx=18, pady=16)
    content_frame.pack(fill="both", expand=True)

    text_color = COLORS["red"] if is_error else COLORS["text"]
    tk.Label(
        content_frame,
        text=message,
        bg=COLORS["base"],
        fg=text_color,
        font=("Segoe UI", 10),
        wraplength=340,
        justify="left"
    ).pack(anchor="w", pady=(0, 18))

    btn_frame = tk.Frame(content_frame, bg=COLORS["base"])
    btn_frame.pack(fill="x")

    def on_close():
        dialog.destroy()

    btn_ok = tk.Button(
        btn_frame,
        text="OK",
        command=on_close,
        bg=COLORS["mauve"] if not is_error else COLORS["red"],
        fg=COLORS["base"],
        relief="flat",
        font=("Segoe UI", 9, "bold"),
        padx=20,
        pady=4,
        cursor="hand2"
    )
    btn_ok.pack(side="right")

    dialog.bind("<Return>", lambda e: on_close())
    dialog.bind("<Escape>", lambda e: on_close())
    dialog.protocol("WM_DELETE_WINDOW", on_close)

    _center_dialog(dialog, parent, 380, 140)
    dialog.wait_window()
