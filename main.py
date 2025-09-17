import time
import threading
import pyautogui
import keyboard
import win32gui

# ===== Globals =====
target_window = None
running = False
paused = False
mode = None  # "coffee" or "pizza"
counts = {"coffee": 0, "pizza": 0}
interval_seconds = 1  # press cadence
_state_lock = threading.Lock()


def set_active_window():
    """Stores the currently active window handle when F9 is pressed."""
    global target_window
    target_window = win32gui.GetForegroundWindow()
    print("✅ Active window set!")


def set_mode_coffee():
    """Toggle to coffee mode (E then C)."""
    global mode
    with _state_lock:
        mode = "coffee"
    print("☕ Mode set: COFFEE (E then C)")


def set_mode_pizza():
    """Toggle to pizza mode (E then Z)."""
    global mode
    with _state_lock:
        mode = "pizza"
    print("🍕 Mode set: PIZZA (E then Z)")


def worker():
    """Background worker that presses keys on the chosen cadence if running and not paused."""
    global running, paused, target_window, mode, counts

    last_press = 0.0
    while True:
        with _state_lock:
            _running = running
            _paused = paused
            _mode = mode
            _target = target_window

        if not _running:
            time.sleep(0.1)
            continue

        if (
            not _paused
            and _mode in ("coffee", "pizza")
            and _target is not None
            and _target == win32gui.GetForegroundWindow()
            and (time.time() - last_press) >= interval_seconds
        ):
            if _mode == "coffee":
                pyautogui.press("e")
                pyautogui.press("c")
                with _state_lock:
                    counts["coffee"] += 1
                    n = counts["coffee"]
                print(f"Pressed E then C - [ {n} ]")
            elif _mode == "pizza":
                pyautogui.press("e")
                pyautogui.press("z")
                with _state_lock:
                    counts["pizza"] += 1
                    n = counts["pizza"]
                print(f"Pressed E then Z - [ {n} ]")

            last_press = time.time()

        time.sleep(0.05)


def start_script():
    """Start or resume the worker loop."""
    global running, paused
    with _state_lock:
        if not running:
            running = True
            paused = False
            threading.Thread(target=worker, daemon=True).start()
            print("▶️ Script started")
        else:
            paused = False
            print("▶️ Script resumed")


def pause_script():
    """Pause the worker loop (does not stop the thread)."""
    global paused
    with _state_lock:
        paused = True
    print("⏸️ Script paused")


# ===== Key bindings =====
keyboard.add_hotkey("f9", set_active_window)     # lock target window
keyboard.add_hotkey("delete", start_script)      # start/resume
keyboard.add_hotkey("esc", pause_script)         # pause

keyboard.add_hotkey("page up", set_mode_coffee)  # Coffee mode
keyboard.add_hotkey("page down", set_mode_pizza) # Pizza mode

print("Controls:")
print("  [F9]        Set active window (target)")
print("  [Delete]    Start / Resume")
print("  [Esc]       Pause")
print("  [Page Up]   Mode: Coffee (E then C)")
print("  [Page Down] Mode: Pizza  (E then Z)")
print("  [Ctrl+Q]    Exit")

keyboard.wait("ctrl+q")
print("Exiting…")