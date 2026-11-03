import ctypes
import gc
import tkinter as tk
from ctypes import wintypes

import psutil

# Windows desktop-layer RAM monitor. Drag the top header to reposition it.
X, Y = 34, 90
WIDTH, HEIGHT = 350, 300

BG = "#0B1220"
PANEL = "#111C2D"
PANEL_2 = "#172438"
FG = "#F4F7FB"
MUTED = "#91A2B8"
ACCENT = "#54E0B0"
BLUE = "#69A9FF"
TRACK = "#26364C"
WARNING = "#F6C66A"

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
HWND = wintypes.HWND

user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = HWND
user32.FindWindowExW.argtypes = [HWND, HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = HWND
user32.GetWindow.argtypes = [HWND, wintypes.UINT]
user32.GetWindow.restype = HWND
user32.SetParent.argtypes = [HWND, HWND]
user32.SetParent.restype = HWND
user32.SendMessageTimeoutW.argtypes = [
    HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
    wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)
]
user32.EnumWindows.argtypes = [
    ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM), wintypes.LPARAM
]
user32.EnumWindows.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    HWND, HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.UINT
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.SetCapture.argtypes = [HWND]
user32.SetCapture.restype = HWND
user32.ReleaseCapture.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.ScreenToClient.argtypes = [HWND, ctypes.POINTER(wintypes.POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
psapi.EmptyWorkingSet.restype = wintypes.BOOL

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
    if not progman:
        return None
    result = ctypes.c_size_t()
    user32.SendMessageTimeoutW(
        progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(result)
    )
    found = [None]
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)

    def enum_callback(hwnd, _):
        view = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if view:
            # Parent to the desktop icon view, not the WorkerW behind it.
            # This allows mouse interaction while app windows cover the widget.
            found[0] = view
            return False
        return True

    user32.EnumWindows(callback_type(enum_callback), 0)
    return found[0] or progman


class DesktopMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RAM Monitor")
        self.root.overrideredirect(True)
        self.root.configure(bg=BG)
        self.root.attributes("-alpha", 0.97)
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{X}+{Y}")
        self.root.resizable(False, False)
        self.position = [X, Y]
        self.drag_origin = None
        self.dragging = False
        self.desktop_parent = None
        self.status_job = None

        outer = tk.Frame(
            self.root, bg=BG, highlightthickness=1,
            highlightbackground="#26364C"
        )
        outer.pack(fill="both", expand=True)

        # The header is the dedicated drag handle. Bind on the toplevel with
        # bind_all so dragging works even when the pointer starts on a label.
        header = tk.Frame(outer, bg=PANEL, cursor="fleur")
        header.pack(fill="x")
        title_area = tk.Frame(header, bg=PANEL, cursor="fleur")
        title_area.pack(side="left", padx=16, pady=13)
        tk.Label(
            title_area, text="◈  SYSTEM PULSE", bg=PANEL, fg=FG,
            font=("Segoe UI", 10, "bold"), cursor="fleur"
        ).pack(anchor="w")
        tk.Label(
            title_area, text="LIVE PERFORMANCE", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 7, "bold"), cursor="fleur"
        ).pack(anchor="w", pady=(2, 0))
        tk.Label(
            header, text="●", bg=PANEL, fg=ACCENT,
            font=("Segoe UI", 11), padx=15, cursor="fleur"
        ).pack(side="right")

        body = tk.Frame(outer, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        memory_card = tk.Frame(body, bg=PANEL_2, padx=13, pady=11)
        memory_card.pack(fill="x")
        top_line = tk.Frame(memory_card, bg=PANEL_2)
        top_line.pack(fill="x")
        tk.Label(
            top_line, text="MEMORY USAGE", bg=PANEL_2, fg=MUTED,
            font=("Segoe UI", 8, "bold")
        ).pack(side="left")
        self.ram_percent = tk.Label(
            top_line, text="--%", bg=PANEL_2, fg=ACCENT,
            font=("Segoe UI", 17, "bold")
        )
        self.ram_percent.pack(side="right")

        self.ram_value = tk.Label(
            memory_card, text="Reading memory…", bg=PANEL_2, fg=FG,
            font=("Segoe UI", 10, "bold")
        )
        self.ram_value.pack(anchor="w", pady=(5, 8))

        self.ram_bar = tk.Canvas(
            memory_card, height=9, bg=TRACK, highlightthickness=0,
            bd=0, relief="flat"
        )
        self.ram_bar.pack(fill="x")
        self.ram_bar.bind("<Configure>", lambda _e: self.root.after_idle(self.redraw_bar))

        stats = tk.Frame(body, bg=BG)
        stats.pack(fill="x", pady=(10, 10))
        self.available_card = self.make_stat_card(
            stats, "AVAILABLE", "-- GB", ACCENT
        )
        self.available_card.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.cpu_card = self.make_stat_card(
            stats, "CPU LOAD", "--%", BLUE
        )
        self.cpu_card.pack(side="left", fill="both", expand=True, padx=(5, 0))

        self.status = tk.Label(
            body, text="Drag the top bar to move this widget",
            bg=BG, fg=MUTED, font=("Segoe UI", 7), anchor="w"
        )
        self.status.pack(fill="x", pady=(0, 8))

        actions = tk.Frame(body, bg=BG)
        actions.pack(fill="x")
        self.optimize_button = tk.Button(
            actions, text="⚡  OPTIMIZE RAM", command=self.optimize_ram,
            bg="#176B55", activebackground="#20856A", fg="#FFFFFF",
            activeforeground="#FFFFFF", relief="flat", bd=0,
            font=("Segoe UI", 8, "bold"), cursor="hand2",
            padx=12, pady=9
        )
        self.optimize_button.pack(side="left", fill="x", expand=True)
        tk.Button(
            actions, text="↻", command=self.refresh, bg=PANEL_2,
            activebackground=TRACK, fg=FG, activeforeground=FG,
            relief="flat", bd=0, font=("Segoe UI", 12, "bold"),
            cursor="hand2", padx=12, pady=5
        ).pack(side="left", padx=(7, 0))
        tk.Button(
            actions, text="×", command=self.root.destroy, bg=PANEL_2,
            activebackground="#713D4A", fg=FG, activeforeground=FG,
            relief="flat", bd=0, font=("Segoe UI", 12),
            cursor="hand2", padx=12, pady=5
        ).pack(side="left", padx=(6, 0))

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Refresh now", command=self.refresh)
        self.menu.add_command(label="Optimize widget memory", command=self.optimize_ram)
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self.root.destroy)

        self.bind_drag_tree(header)
        self.root.bind("<Button-3>", self.show_menu)
        self.root.after(700, self.attach_to_desktop)
        self.refresh()

    def make_stat_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg=PANEL, padx=11, pady=9)
        tk.Label(
            card, text=title, bg=PANEL, fg=MUTED,
            font=("Segoe UI", 7, "bold")
        ).pack(anchor="w")
        number = tk.Label(
            card, text=value, bg=PANEL, fg=color,
            font=("Segoe UI", 14, "bold")
        )
        number.pack(anchor="w", pady=(3, 0))
        card.value_label = number
        return card

    def bind_drag_tree(self, widget):
        # Bind all header descendants, including labels.
        widget.bind("<ButtonPress-1>", self.start_drag, add="+")
        widget.bind("<B1-Motion>", self.drag_widget, add="+")
        widget.bind("<ButtonRelease-1>", self.stop_drag, add="+")
        for child in widget.winfo_children():
            self.bind_drag_tree(child)

    def start_drag(self, event):
        parent = self.desktop_parent
        if not parent:
            return
        rect = wintypes.RECT()
        if not user32.GetWindowRect(self.root.winfo_id(), ctypes.byref(rect)):
            return
        point = wintypes.POINT(rect.left, rect.top)
        if not user32.ScreenToClient(parent, ctypes.byref(point)):
            return
        self.drag_origin = (event.x_root, event.y_root, point.x, point.y)
        self.dragging = True
        user32.SetCapture(self.root.winfo_id())

    def drag_widget(self, event):
        if not self.dragging or not self.drag_origin or not self.desktop_parent:
            return
        sx, sy, ox, oy = self.drag_origin
        nx = ox + event.x_root - sx
        ny = oy + event.y_root - sy
        if user32.SetWindowPos(self.root.winfo_id(), None, nx, ny, WIDTH, HEIGHT,
                               SWP_NOZORDER | SWP_NOACTIVATE):
            self.position = [nx, ny]

    def stop_drag(self, _event):
        if self.dragging:
            user32.ReleaseCapture()
        self.dragging = False
        self.drag_origin = None

    def show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def attach_to_desktop(self):
        hwnd = self.root.winfo_id()
        parent = find_desktop_layer()
        if not parent:
            self.set_status("Desktop layer unavailable — widget remains open")
            return
        user32.SetParent(hwnd, parent)
        self.desktop_parent = parent
        style = get_window_long(hwnd, GWL_STYLE)
        set_window_long(
            hwnd, GWL_STYLE, (style | WS_CHILD | WS_VISIBLE) & ~WS_POPUP
        )
        user32.SetWindowPos(
            hwnd, None, self.position[0], self.position[1], WIDTH, HEIGHT,
            SWP_NOACTIVATE | SWP_FRAMECHANGED
        )

    def redraw_bar(self):
        try:
            self.draw_bar(psutil.virtual_memory().percent)
        except (psutil.Error, tk.TclError):
            pass

    def draw_bar(self, percent):
        self.ram_bar.delete("all")
        width = max(1, self.ram_bar.winfo_width())
        height = max(1, self.ram_bar.winfo_height())
        self.ram_bar.create_rectangle(
            0, 0, width, height, fill=TRACK, outline=""
        )
        fill = int(width * max(0, min(100, percent)) / 100)
        color = WARNING if percent >= 85 else ACCENT
        if fill:
            self.ram_bar.create_rectangle(
                0, 0, fill, height, fill=color, outline=""
            )

    def set_status(self, message):
        self.status.config(text=message)
        if self.status_job:
            self.root.after_cancel(self.status_job)
        self.status_job = self.root.after(
            5000, lambda: self.status.config(
                text="Drag the top bar to move this widget"
            )
        )

    def refresh(self):
        try:
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=None)
            total_gb = memory.total / (1024 ** 3)
            used_gb = memory.used / (1024 ** 3)
            available_gb = memory.available / (1024 ** 3)
            self.ram_percent.config(text=f"{memory.percent:.0f}%")
            self.ram_value.config(
                text=f"{used_gb:.1f} GB used  /  {total_gb:.1f} GB total"
            )
            self.available_card.value_label.config(text=f"{available_gb:.1f} GB")
            self.cpu_card.value_label.config(text=f"{cpu:.0f}%")
            self.root.update_idletasks()
            self.draw_bar(memory.percent)
        except (psutil.Error, tk.TclError):
            pass
        self.root.after(2000, self.refresh)

    def optimize_ram(self):
        # This safely trims this widget's own working set only. Windows manages
        # other applications and the system file cache; we do not kill processes
        # or claim to free memory owned by other apps.
        try:
            gc.collect()
            handle = kernel32.GetCurrentProcess()
            trimmed = bool(psapi.EmptyWorkingSet(handle))
            self.refresh()
            if trimmed:
                self.set_status("Widget memory trimmed • Windows manages system RAM")
            else:
                self.set_status("Cleanup complete • Windows manages system RAM")
        except Exception:
            self.set_status("Could not trim widget memory on this system")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    DesktopMonitor().run()
