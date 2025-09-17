import threading
import time
import json
import os
import pyautogui
import keyboard
import win32gui
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox

# ======================= Core State =======================
target_window = None
running = False
paused = False
mode = None  # "coffee" or "pizza"
counts = {"coffee": 0, "pizza": 0}
interval_seconds = 5.0  # default cadence
_state_lock = threading.Lock()
_worker_thread_started = False

# Where to store/load presets
PRESET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_order_theme.json")

# Defaults
DEFAULT_COLORS = {
    "window_bg": "#0f172a",           # slate-900
    "text": "#e2e8f0",                # slate-200
    "button_active_bg": "#16a34a",    # green-600
    "button_inactive_bg": "#334155",  # slate-700
    "counter_bg": "#1f2937",          # gray-800
}
DEFAULT_INTERVAL = 5.0

# ======================= GUI App ==========================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto-Order Helper")
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        self.root.resizable(False, False)

        # ---- Theme (customizable via Settings) ----
        self.colors = DEFAULT_COLORS.copy()
        self.style = ttk.Style()
        # Set base bg immediately so early widgets don't flash white
        self.root.configure(bg=self.colors["window_bg"])

        # --------------- Layout ---------------
        pad_x = 8
        pad_y = 6

        # ---- Header ----
        self.header = ttk.Label(self.root, text="Auto-Order Helper", font=("Segoe UI", 16, "bold"))
        self.header.grid(row=0, column=0, columnspan=4, pady=(10, 6), padx=10, sticky="w")

        # ---- Top Controls (tk.Button so we can color them) ----
        self.btn_set_window = tk.Button(self.root, text="Set Active Window", command=self.set_active_window)
        self.btn_start = tk.Button(self.root, text="Start", command=self.start_script)
        self.btn_pause = tk.Button(self.root, text="Pause", command=self.pause_script)
        self.btn_settings = tk.Button(self.root, text="Settings", command=self.open_settings)

        self.btn_set_window.grid(row=1, column=0, padx=pad_x, pady=pad_y, sticky="ew")
        self.btn_start.grid(row=1, column=1, padx=pad_x, pady=pad_y, sticky="ew")
        self.btn_pause.grid(row=1, column=2, padx=pad_x, pady=pad_y, sticky="ew")
        self.btn_settings.grid(row=1, column=3, padx=pad_x, pady=pad_y, sticky="ew")

        # ---- Mode Buttons (tk.Button, color-toggling) ----
        self.btn_coffee = tk.Button(self.root, text="☕ Coffee (E → C)", command=self.set_mode_coffee,
                                    font=("Segoe UI", 10, "bold"))
        self.btn_pizza  = tk.Button(self.root, text="🍕 Pizza  (E → Z)", command=self.set_mode_pizza,
                                    font=("Segoe UI", 10, "bold"))
        self.btn_coffee.grid(row=2, column=0, columnspan=2, padx=pad_x, pady=(0, pad_y), sticky="ew")
        self.btn_pizza.grid(row=2, column=2, columnspan=2, padx=pad_x, pady=(0, pad_y), sticky="ew")

        # ---- Counters + Reset ----
        self.counter_frame = tk.Frame(self.root, bd=0)
        self.counter_frame.grid(row=3, column=0, columnspan=4, padx=pad_x, pady=pad_y, sticky="ew")
        self.lbl_coffee_count = ttk.Label(self.counter_frame, text="Coffee Count: 0", font=("Segoe UI", 12, "bold"))
        self.lbl_pizza_count = ttk.Label(self.counter_frame, text="Pizza Count: 0", font=("Segoe UI", 12, "bold"))
        self.lbl_state = ttk.Label(self.counter_frame, text="State: Stopped | Mode: — | Target: None", font=("Segoe UI", 10))
        self.btn_reset = tk.Button(self.counter_frame, text="Reset Counters", command=self.reset_counters)

        self.lbl_coffee_count.pack(side="left", padx=10, pady=8)
        self.lbl_pizza_count.pack(side="left", padx=10, pady=8)
        self.btn_reset.pack(side="left", padx=10, pady=8)
        self.lbl_state.pack(side="right", padx=10, pady=8)

        # ---- Legend ----
        legend = (
            "Keybinds:\n"
            "  F9        → Set active window\n"
            "  Delete    → Start / Resume\n"
            "  Esc       → Pause\n"
            "  Page Up   → Mode: Coffee (E then C)\n"
            "  Page Down → Mode: Pizza  (E then Z)\n"
            "  Ctrl+Q    → Quit"
        )
        self.legend_box = tk.Text(self.root, height=7, width=56, bd=0)
        self.legend_box.insert("1.0", legend)
        self.legend_box.configure(state="disabled")
        self.legend_box.grid(row=4, column=0, columnspan=4, padx=pad_x, pady=(0, 10), sticky="ew")

        # ---- Responsive columns ----
        for c in range(4):
            self.root.grid_columnconfigure(c, weight=1)

        # ---- Hotkeys ----
        keyboard.add_hotkey("f9", self.set_active_window)
        keyboard.add_hotkey("delete", self.start_script)
        keyboard.add_hotkey("esc", self.pause_script)
        keyboard.add_hotkey("page up", self.set_mode_coffee)
        keyboard.add_hotkey("page down", self.set_mode_pizza)
        keyboard.add_hotkey("ctrl+q", self.on_quit)

        # Now that widgets exist, apply theme/colors safely
        self._apply_theme()
        self._refresh_all_colors()
        self._refresh_button_styles()
        self._update_state_label()

        # Try auto-load preset (if exists) AFTER base paint so we can update live
        self.try_autoload_preset()

        # Start UI poller
        self._ui_updater()

    # ---------- Theme ----------
    def _apply_theme(self):
        # Window + ttk labels
        self.root.configure(bg=self.colors["window_bg"])
        self.style.theme_use("default")
        self.style.configure("TLabel",
            background=self.colors["window_bg"],
            foreground=self.colors["text"]
        )
        # Safely paint widgets that may or may not exist yet
        if hasattr(self, "legend_box"):
            self.legend_box.configure(
                bg=self.colors["window_bg"],
                fg=self.colors["text"],
                insertbackground=self.colors["text"],
            )
        if hasattr(self, "counter_frame"):
            self.counter_frame.configure(bg=self.colors["counter_bg"])

    def _refresh_all_colors(self):
        # Apply colors to every tk.Button
        btns = [
            self.btn_set_window, self.btn_start, self.btn_pause, self.btn_settings,
            self.btn_coffee, self.btn_pizza, self.btn_reset
        ]
        for b in btns:
            b.configure(
                bg=self.colors["button_inactive_bg"],
                fg=self.colors["text"],
                activebackground=self.colors["button_inactive_bg"],
                activeforeground=self.colors["text"],
                relief="flat",
                bd=0,
                padx=8, pady=6
            )

    def _refresh_button_styles(self):
        # Highlight current mode button
        with _state_lock:
            m = mode
        if m == "coffee":
            self.btn_coffee.configure(bg=self.colors["button_active_bg"], activebackground=self.colors["button_active_bg"])
            self.btn_pizza.configure(bg=self.colors["button_inactive_bg"], activebackground=self.colors["button_inactive_bg"])
        elif m == "pizza":
            self.btn_pizza.configure(bg=self.colors["button_active_bg"], activebackground=self.colors["button_active_bg"])
            self.btn_coffee.configure(bg=self.colors["button_inactive_bg"], activebackground=self.colors["button_inactive_bg"])
        else:
            self.btn_coffee.configure(bg=self.colors["button_inactive_bg"], activebackground=self.colors["button_inactive_bg"])
            self.btn_pizza.configure(bg=self.colors["button_inactive_bg"], activebackground=self.colors["button_inactive_bg"])

    # ---------- Controls ----------
    def set_active_window(self):
        global target_window
        target_window = win32gui.GetForegroundWindow()
        self._update_state_label()

    def set_mode_coffee(self):
        global mode
        with _state_lock:
            mode = "coffee"
        self._refresh_button_styles()
        self._update_state_label()

    def set_mode_pizza(self):
        global mode
        with _state_lock:
            mode = "pizza"
        self._refresh_button_styles()
        self._update_state_label()

    def start_script(self):
        global running, paused, _worker_thread_started
        with _state_lock:
            if not _worker_thread_started:
                threading.Thread(target=worker, daemon=True).start()
                _worker_thread_started = True
            running = True
            paused = False
        self._update_state_label()

    def pause_script(self):
        global paused
        with _state_lock:
            paused = True
        self._update_state_label()

    def reset_counters(self):
        with _state_lock:
            counts["coffee"] = 0
            counts["pizza"] = 0
        # UI will update on next tick

    # ---------- Settings ----------
    def open_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings")
        dlg.resizable(False, False)
        dlg.configure(bg=self.colors["window_bg"])

        def row_color(label, key):
            frame = tk.Frame(dlg, bg=self.colors["window_bg"])
            frame.pack(fill="x", padx=10, pady=6)
            ttk.Label(frame, text=label).pack(side="left")
            preview = tk.Canvas(frame, width=40, height=20, highlightthickness=1, highlightbackground="#000",
                                bg=self.colors["window_bg"])
            preview.pack(side="left", padx=10)
            rect = preview.create_rectangle(0, 0, 40, 20, fill=self.colors[key], outline="")
            def pick():
                _, hexcolor = colorchooser.askcolor(color=self.colors[key], title=f"Pick {label} color")
                if hexcolor:
                    self.colors[key] = hexcolor
                    preview.itemconfigure(rect, fill=hexcolor)
                    # Repaint live
                    self._apply_theme()
                    self._refresh_all_colors()
                    self._refresh_button_styles()
            tk.Button(frame, text="Choose…", command=pick,
                      bg=self.colors["button_inactive_bg"], fg=self.colors["text"],
                      activebackground=self.colors["button_inactive_bg"],
                      activeforeground=self.colors["text"], relief="flat", bd=0, padx=6, pady=4).pack(side="left")

        # Color pickers
        row_color("Window Background", "window_bg")
        row_color("Text Color", "text")
        row_color("Active Button", "button_active_bg")
        row_color("Inactive Button", "button_inactive_bg")
        row_color("Counter Strip", "counter_bg")

        # Interval slider
        sep = ttk.Separator(dlg, orient="horizontal")
        sep.pack(fill="x", padx=10, pady=8)

        interval_frame = tk.Frame(dlg, bg=self.colors["window_bg"])
        interval_frame.pack(fill="x", padx=10, pady=6)
        ttk.Label(interval_frame, text="Press Cadence (seconds)").pack(anchor="w")

        # Bind to global interval
        self.interval_var = tk.DoubleVar(value=float(interval_seconds))
        slider = ttk.Scale(
            interval_frame, from_=0.5, to=10.0, variable=self.interval_var,
            command=lambda _evt=None: self._apply_interval_from_slider()
        )
        slider.pack(fill="x", padx=2, pady=4)
        self.interval_label = ttk.Label(interval_frame, text=f"{self.interval_var.get():.1f} s")
        self.interval_label.pack(anchor="e")

        # Preset control buttons
        btn_row = tk.Frame(dlg, bg=self.colors["window_bg"])
        btn_row.pack(fill="x", padx=10, pady=(8, 10))

        tk.Button(btn_row, text="Save Preset", command=self.save_preset,
                  bg=self.colors["button_inactive_bg"], fg=self.colors["text"],
                  activebackground=self.colors["button_inactive_bg"],
                  activeforeground=self.colors["text"], relief="flat", bd=0, padx=8, pady=6).pack(side="left")

        tk.Button(btn_row, text="Load Preset", command=lambda: self.load_preset(show_messages=True),
                  bg=self.colors["button_inactive_bg"], fg=self.colors["text"],
                  activebackground=self.colors["button_inactive_bg"],
                  activeforeground=self.colors["text"], relief="flat", bd=0, padx=8, pady=6).pack(side="left", padx=8)

        tk.Button(btn_row, text="Reset to Defaults", command=self.reset_to_defaults,
                  bg=self.colors["button_inactive_bg"], fg=self.colors["text"],
                  activebackground=self.colors["button_inactive_bg"],
                  activeforeground=self.colors["text"], relief="flat", bd=0, padx=8, pady=6).pack(side="left")

        # Path hint
        hint = ttk.Label(dlg, text=f"Preset file: {PRESET_PATH}")
        hint.pack(anchor="w", padx=10, pady=(0, 6))

    def _apply_interval_from_slider(self):
        val = max(0.1, float(self.interval_var.get()))
        with _state_lock:
            global interval_seconds
            interval_seconds = val
        self.interval_label.config(text=f"{val:.1f} s")

    # ---------- Preset Save/Load/Reset ----------
    def save_preset(self):
        data = {
            "colors": self.colors,
            "interval_seconds": float(interval_seconds),
        }
        try:
            with open(PRESET_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Preset Saved", f"Theme preset saved to:\n{PRESET_PATH}")
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save preset:\n{e}")

    def load_preset(self, show_messages=False):
        try:
            if not os.path.exists(PRESET_PATH):
                if show_messages:
                    messagebox.showwarning("Load Preset", "No preset file found.")
                return
            with open(PRESET_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            colors = data.get("colors", {})
            interval = data.get("interval_seconds", DEFAULT_INTERVAL)

            # Apply colors (validate keys; fallback to defaults if missing/invalid)
            for k, v in DEFAULT_COLORS.items():
                if isinstance(colors.get(k), str) and colors.get(k).startswith("#"):
                    self.colors[k] = colors[k]
                else:
                    self.colors[k] = v

            # Apply interval
            try:
                val = float(interval)
                with _state_lock:
                    global interval_seconds
                    interval_seconds = max(0.1, min(val, 60.0))
            except Exception:
                with _state_lock:
                    interval_seconds = DEFAULT_INTERVAL

            # Repaint UI
            self._apply_theme()
            self._refresh_all_colors()
            self._refresh_button_styles()
            self._update_state_label()

            # If a settings window is open, update its slider if found
            try:
                if hasattr(self, "interval_var"):
                    self.interval_var.set(interval_seconds)
                if hasattr(self, "interval_label"):
                    self.interval_label.config(text=f"{interval_seconds:.1f} s")
            except Exception:
                pass

            if show_messages:
                messagebox.showinfo("Preset Loaded", "Preset applied.")
        except Exception as e:
            if show_messages:
                messagebox.showerror("Load Failed", f"Could not load preset:\n{e}")

    def reset_to_defaults(self):
        # Reset to defaults
        self.colors = DEFAULT_COLORS.copy()
        with _state_lock:
            global interval_seconds
            interval_seconds = DEFAULT_INTERVAL

        self._apply_theme()
        self._refresh_all_colors()
        self._refresh_button_styles()
        self._update_state_label()

        # Update any open settings controls
        try:
            if hasattr(self, "interval_var"):
                self.interval_var.set(interval_seconds)
            if hasattr(self, "interval_label"):
                self.interval_label.config(text=f"{interval_seconds:.1f} s")
        except Exception:
            pass

        messagebox.showinfo("Defaults Restored", "Colors and cadence reset to defaults.")

    def try_autoload_preset(self):
        # Silent auto-load on startup if file exists
        if os.path.exists(PRESET_PATH):
            self.load_preset(show_messages=False)

    # ---------- UI Updates ----------
    def _ui_updater(self):
        with _state_lock:
            c = counts["coffee"]
            p = counts["pizza"]
        self.lbl_coffee_count.config(text=f"Coffee Count: {c}")
        self.lbl_pizza_count.config(text=f"Pizza Count: {p}")
        self._refresh_button_styles()
        self.root.after(150, self._ui_updater)

    def _update_state_label(self):
        with _state_lock:
            r = "Running" if running and not paused else ("Paused" if running and paused else "Stopped")
            m = "☕ COFFEE" if mode == "coffee" else ("🍕 PIZZA" if mode == "pizza" else "—")
            tgt = self._window_title(target_window) if target_window else "None"
        self.lbl_state.config(text=f"State: {r} | Mode: {m} | Target: {tgt}")

    @staticmethod
    def _window_title(hwnd):
        try:
            title = win32gui.GetWindowText(hwnd)
            return title if title else "(untitled)"
        except Exception:
            return "(unknown)"

    # ---------- Quit ----------
    def on_quit(self):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self.root.after(50, self.root.destroy)

# ======================= Worker ==========================
def worker():
    global running, paused, target_window, mode, counts, interval_seconds

    last_press = 0.0
    while True:
        with _state_lock:
            _running = running
            _paused = paused
            _mode = mode
            _target = target_window
            _interval = float(interval_seconds)

        if not _running:
            time.sleep(0.1)
            continue

        if (
            not _paused
            and _mode in ("coffee", "pizza")
            and _target is not None
            and _target == win32gui.GetForegroundWindow()
            and (time.time() - last_press) >= _interval
        ):
            if _mode == "coffee":
                pyautogui.press("e"); pyautogui.press("c")
                with _state_lock:
                    counts["coffee"] += 1
                    n = counts["coffee"]
                print(f"Pressed E then C - [ {n} ]")
            elif _mode == "pizza":
                pyautogui.press("e"); pyautogui.press("z")
                with _state_lock:
                    counts["pizza"] += 1
                    n = counts["pizza"]
                print(f"Pressed E then Z - [ {n} ]")
            last_press = time.time()

        time.sleep(0.05)

# ======================= Main ============================
if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
