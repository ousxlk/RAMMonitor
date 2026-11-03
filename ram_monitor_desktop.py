import ctypes
import tkinter as tk
from tkinter import ttk
import psutil
import time

# Desktop position (pixels from the top-left of the primary monitor).
X, Y = 34, 90
BG = "#101820"
FG = "#F2F6FA"
MUTED = "#9EADB9"
ACCENT = "#54D6A0"
BAR_BG = "#293844"

user32 = ctypes.windll.user32
# Explicit pointer-sized return types are required on 64-bit Windows.
user32.FindWindowW.restype = ctypes.c_void_p
user32.FindWindowExW.restype = ctypes.c_void_p
user32.GetWindow.restype = ctypes.c_void_p
user32.SetParent.restype = ctypes.c_void_p
GWL_STYLE = -16
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
GW_HWNDNEXT = 2

def desktop_worker():
    progman = user32.FindWindowW("Progman", None)
    result = ctypes.c_ulong()
    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(result))
    worker = None
    enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visit(hwnd, _):
        nonlocal worker
        shell = user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None)
        if shell:
            worker = user32.GetWindow(hwnd, GW_HWNDNEXT)
            return False
        return True
    user32.EnumWindows(enum_proc_type(visit), 0)
    return worker or progman

class DesktopMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RAM Monitor Desktop Widget")
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)
        self.root.attributes("-alpha", 0.92)
        self.root.geometry(f"270x190+{X}+{Y}")
        self.root.resizable(False, False)

        outer = tk.Frame(self.root, bg=BG, highlightthickness=1, highlightbackground="#344653")
        outer.pack(fill="both", expand=True)
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", padx=14, pady=(11, 5))
        tk.Label(header, text="SYSTEM MONITOR", bg=BG, fg=FG,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(header, text="● LIVE", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 8, "bold")).pack(side="right")

        self.rows = {}
        for key, label in (("ram", "MEMORY"), ("cpu", "PROCESSOR")):
            block = tk.Frame(outer, bg=BG)
            block.pack(fill="x", padx=14, pady=5)
            line = tk.Frame(block, bg=BG)
            line.pack(fill="x")
            tk.Label(line, text=label, bg=BG, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            value = tk.Label(line, text="…", bg=BG, fg=FG,
                             font=("Segoe UI", 9, "bold"))
            value.pack(side="right")
            bar = tk.Canvas(block, height=6, bg=BAR_BG, highlightthickness=0)
            bar.pack(fill="x", pady=(5, 0))
            self.rows[key] = (value, bar)

        self.detail = tk.Label(outer, text="Available memory: —",
                               bg=BG, fg=MUTED, font=("Segoe UI", 8))
        self.detail.pack(anchor="w", padx=14, pady=(5, 0))
        self.footer = tk.Label(outer, text="Right-click for options",
                               bg=BG, fg="#718391", font=("Segoe UI", 7))
        self.footer.pack(anchor="w", padx=14, pady=(3, 9))

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Refresh now", command=self.update)
        menu.add_command(label="Exit", command=self.root.destroy)
        self.root.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
        for child in self.root.winfo_children():
            child.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
        self.root.after(400, self.attach_to_desktop)
        self.update()

    def attach_to_desktop(self):
        hwnd = self.root.winfo_id()
        parent = desktop_worker()
        if parent:
            user32.SetParent(hwnd, parent)
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            style = (style | WS_CHILD | WS_VISIBLE) & ~WS_POPUP
            user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            user32.SetWindowPos(hwnd, 0, X, Y, 270, 190, 0x0010 | 0x0040)

    def set_bar(self, canvas, percent):
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        canvas.create_rectangle(0, 0, width, 6, fill=BAR_BG, outline="")
        fill = int(width * max(0, min(100, percent)) / 100)
        canvas.create_rectangle(0, 0, fill, 6, fill=ACCENT, outline="")

    def update(self):
        try:
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=None)
            self.rows["ram"][0].config(text=f"{mem.percent:.0f}%  ·  {mem.used / 1024**3:.1f} / {mem.total / 1024**3:.1f} GB")
            self.rows["cpu"][0].config(text=f"{cpu:.0f}%")
            self.detail.config(text=f"Available memory: {mem.available / 1024**3:.1f} GB")
            self.root.update_idletasks()
            self.set_bar(self.rows["ram"][1], mem.percent)
            self.set_bar(self.rows["cpu"][1], cpu)
        except Exception:
            pass
        self.root.after(2000, self.update)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    DesktopMonitor().run()
