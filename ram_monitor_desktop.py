import ctypes
import tkinter as tk
from ctypes import wintypes
import psutil

# Desktop position, measured from the top-left corner of the primary display.
X, Y = 34, 90
WIDTH, HEIGHT = 286, 196
BG, FG = "#101820", "#F2F6FA"
MUTED, ACCENT, BAR_BG = "#9EADB9", "#54D6A0", "#293844"

user32 = ctypes.WinDLL("user32", use_last_error=True)
HWND = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = HWND
user32.FindWindowExW.argtypes = [HWND, HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = HWND
user32.GetWindow.argtypes = [HWND, wintypes.UINT]
user32.GetWindow.restype = HWND
user32.SetParent.argtypes = [HWND, HWND]
user32.SetParent.restype = HWND
user32.SendMessageTimeoutW.argtypes = [HWND, wintypes.UINT, wintypes.WPARAM,
                                       wintypes.LPARAM, wintypes.UINT,
                                       wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM),
                               wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [HWND, HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL

GWL_STYLE = -16
WS_CHILD, WS_POPUP, WS_VISIBLE = 0x40000000, 0x80000000, 0x10000000
GW_HWNDNEXT = 2
SWP_NOZORDER, SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x0004, 0x0010, 0x0020

if ctypes.sizeof(ctypes.c_void_p) == 8:
    get_window_long = user32.GetWindowLongPtrW
    set_window_long = user32.SetWindowLongPtrW
    get_window_long.restype = ctypes.c_ssize_t
    set_window_long.restype = ctypes.c_ssize_t
else:
    get_window_long = user32.GetWindowLongW
    set_window_long = user32.SetWindowLongW
    get_window_long.restype = ctypes.c_long
    set_window_long.restype = ctypes.c_long
get_window_long.argtypes = [HWND, ctypes.c_int]
set_window_long.argtypes = [HWND, ctypes.c_int, ctypes.c_ssize_t]

def find_desktop_layer():
    progman = user32.FindWindowW("Progman", None)
    result = ctypes.c_size_t()
    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000,
                               ctypes.byref(result))
    found = [None]
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)

    def enum_callback(hwnd, _):
        view = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if view:
            found[0] = user32.GetWindow(hwnd, GW_HWNDNEXT)
            return False
        return True

    user32.EnumWindows(callback_type(enum_callback), 0)
    return found[0] or progman

class DesktopMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RAM Monitor Desktop Widget")
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)
        self.root.attributes("-alpha", 0.94)
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{X}+{Y}")
        self.root.resizable(False, False)
        self.position = [X, Y]
        self.drag_origin = None

        panel = tk.Frame(self.root, bg=BG, highlightthickness=1,
                         highlightbackground="#344653")
        panel.pack(fill="both", expand=True)
        header = tk.Frame(panel, bg=BG)
        header.pack(fill="x", padx=15, pady=(12, 7))
        tk.Label(header, text="SYSTEM MONITOR", bg=BG, fg=FG,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(header, text="● LIVE", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 8, "bold")).pack(side="right")

        self.rows = {}
        for key, title in (("ram", "MEMORY"), ("cpu", "PROCESSOR")):
            section = tk.Frame(panel, bg=BG)
            section.pack(fill="x", padx=15, pady=5)
            line = tk.Frame(section, bg=BG)
            line.pack(fill="x")
            tk.Label(line, text=title, bg=BG, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            value = tk.Label(line, text="Reading…", bg=BG, fg=FG,
                             font=("Segoe UI", 9, "bold"))
            value.pack(side="right")
            bar = tk.Canvas(section, height=6, bg=BAR_BG, highlightthickness=0)
            bar.pack(fill="x", pady=(5, 0))
            self.rows[key] = (value, bar)

        self.available = tk.Label(panel, text="Available memory: —",
                                  bg=BG, fg=MUTED, font=("Segoe UI", 8))
        self.available.pack(anchor="w", padx=15, pady=(5, 0))
        tk.Label(panel, text="Drag to move  ·  Right-click for options", bg=BG, fg="#718391",
                 font=("Segoe UI", 7)).pack(anchor="w", padx=15, pady=(4, 9))

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Refresh now", command=self.refresh)
        menu.add_separator()
        menu.add_command(label="Exit", command=self.root.destroy)
        self.root.bind("<Button-3>", lambda event: self.show_menu(menu, event))
        self.bind_drag(self.root)
        self.root.after(500, self.attach_to_desktop)
        self.refresh()

    def bind_drag(self, widget):
        # Bind the whole widget surface so it can be moved from any blank area.
        widget.bind("<ButtonPress-1>", self.start_drag, add="+")
        widget.bind("<B1-Motion>", self.drag_widget, add="+")
        for child in widget.winfo_children():
            self.bind_drag(child)

    def start_drag(self, event):
        self.drag_origin = (event.x_root, event.y_root,
                            self.position[0], self.position[1])

    def drag_widget(self, event):
        if not self.drag_origin:
            return
        sx, sy, ox, oy = self.drag_origin
        nx, ny = ox + event.x_root - sx, oy + event.y_root - sy
        hwnd = self.root.winfo_id()
        if user32.SetWindowPos(hwnd, None, nx, ny, WIDTH, HEIGHT,
                               SWP_NOZORDER | SWP_NOACTIVATE):
            self.position = [nx, ny]

    @staticmethod
    def show_menu(menu, event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def attach_to_desktop(self):
        hwnd = self.root.winfo_id()
        parent = find_desktop_layer()
        if parent:
            user32.SetParent(hwnd, parent)
            style = get_window_long(hwnd, GWL_STYLE)
            set_window_long(hwnd, GWL_STYLE,
                            (style | WS_CHILD | WS_VISIBLE) & ~WS_POPUP)
            user32.SetWindowPos(hwnd, None, X, Y, WIDTH, HEIGHT,
                                SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)

    def draw_bar(self, canvas, percent):
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        canvas.create_rectangle(0, 0, width, 6, fill=BAR_BG, outline="")
        fill = int(width * max(0, min(100, percent)) / 100)
        if fill:
            canvas.create_rectangle(0, 0, fill, 6, fill=ACCENT, outline="")

    def refresh(self):
        try:
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=None)
            self.rows["ram"][0].config(
                text=f"{memory.percent:.0f}%  ·  {memory.used / 1024**3:.1f} / {memory.total / 1024**3:.1f} GB")
            self.rows["cpu"][0].config(text=f"{cpu:.0f}%")
            self.available.config(
                text=f"Available memory: {memory.available / 1024**3:.1f} GB")
            self.root.update_idletasks()
            self.draw_bar(self.rows["ram"][1], memory.percent)
            self.draw_bar(self.rows["cpu"][1], cpu)
        except (psutil.Error, tk.TclError):
            pass
        self.root.after(2000, self.refresh)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    DesktopMonitor().run()
