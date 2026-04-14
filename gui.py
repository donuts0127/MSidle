import cv2
import numpy as np
import time
import random
import subprocess
import os
import threading
import tkinter as tk
from config import *
import sys, os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
# import easyocr

ASSETS_PATH = resource_path("assets")

# reader = easyocr.Reader(['en'], gpu=True)

# ---------------------------
# GLOBAL STATE
# ---------------------------
active_devices = set()
threads = {}
bot_running = False  # ✅ CONTROL FLAG

# ---------------------------
# What features to enable with checkboxes
# ---------------------------
feature_flags = {
    "npc_chat": True,
    "pt_dc": True,
    "joined_party": True,
    "invited_pq": True,
    "crash": True,
    "login": True,
}

# ---------------------------
# Logger Display
# ---------------------------
log_widget = None

def log(msg):
    global log_widget
    print(msg)  # still print to terminal

    if log_widget:
        log_widget.config(state="normal")
        log_widget.insert(tk.END, msg + "\n")
        log_widget.see(tk.END)
        log_widget.config(state="disabled")
# ---------------------------
# GET DEVICES (ONLY LDPLAYER)
# ---------------------------
def get_devices():
    try:
        output = subprocess.check_output("adb devices", shell=True).decode()
    except:
        return []

    lines = output.splitlines()
    devices = []

    for line in lines:
        if "\tdevice" in line:
            device_id = line.split()[0]
            if device_id.startswith("127.0.0.1"):
                devices.append(device_id)

    return devices

# ---------------------------
# SAFE RUN
# ---------------------------
def safe_run(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if "not found" in result.stderr.lower():
            return False
        return True
    except:
        return False

# ---------------------------
# SCREENSHOT
# ---------------------------
def adb_screencap(device):
    try:
        result = subprocess.run(
            f"adb -s {device} exec-out screencap -p",
            shell=True,
            capture_output=True
        )

        if result.returncode != 0 or not result.stdout:
            return None

        img_array = np.frombuffer(result.stdout, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        return img

    except:
        return None

def jitter(x, y, amount=4):
    return (
        x + random.randint(-amount, amount),
        y + random.randint(-amount, amount)
    )

# ---------------------------
# TAP
# ---------------------------
def adb_tap(device, x, y, jitter_amount):
    jx, jy = jitter(x, y, jitter_amount)
    return safe_run(f"adb -s {device} shell input tap {jx} {jy}")

# ---------------------------
# IMAGE DETECTION
# ---------------------------
def find_image(gray, template_name):
    template_path = os.path.join(ASSETS_PATH, template_name)
    template = cv2.imread(template_path, 0)

    if template is None:
        return None

    res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    if max_val >= THRESHOLD:
        h, w = template.shape
        return (max_loc[0] + w // 2, max_loc[1] + h // 2)

    return None

# ---------------------------
# HUMAN DELAY
# ---------------------------
def human_delay():
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

# ---------------------------
# BOT LOOP PER DEVICE
# ---------------------------
def run_bot(device):
    global bot_running

    log(f"[{device}] Bot thread started")

    while True:
        # ⛔ PAUSE BOT
        if not bot_running:
            time.sleep(0.2)
            continue

        if device not in get_devices():
            log(f"[{device}] DISCONNECTED")
            break

        img = adb_screencap(device)
        if img is None:
            log(f"[{device}] Screenshot failed")
            break

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Priority 1
        if feature_flags["npc_chat"]:
            pos = find_image(gray, "npcChat.png")
            if pos and pos[0] > 550 and pos[1] > 300:
                adb_tap(device, *pos, 5)
                human_delay()
                continue
            # case where npc chat opens wrong window
            pos = find_image(gray, "falseNPC.png")
            if pos:
                pos2 = find_image(gray, "falseNPCok.png")
                if pos2:
                    adb_tap(device, *pos2, 2)
                    human_delay()
                    continue
                continue
            

        # Priority 2
        if feature_flags["pt_dc"]:
            pos = find_image(gray, "ptStopped.png")
            if pos:
                pos2 = find_image(gray, "ptDC.png")
                if pos2:
                    adb_tap(device, *pos2, 7)
                    human_delay()
                    continue
                continue
            

        # Priority 3
        if feature_flags["joined_party"]:
            pos = find_image(gray, "joinedParty.png")
            if pos:
                x, y = 520, 360
                b, g, r = img[y, x]
                if r > 150 and g > 150 and b < 100:
                    pos3 = find_image(gray, "enterPQ.png")
                    if pos3:
                        b1, g1, r1 = img[pos3[1]+6, pos3[0]+6]
                        if b1 > r1 and b1 > g1:
                            log(f"[{device}] enterPQ")
                            adb_tap(device, *pos3, 9)
                            human_delay()
                            continue
                        continue
                    continue
                continue
            

        # Priority 4
        if feature_flags["invited_pq"]:
            pos = find_image(gray, "invitedPQ.png")
            if pos:
                pos2 = find_image(gray, "acceptPQ.png")
                if pos2:
                    b, g, r = img[pos2[1], pos2[0]]
                    if b > r and b > g:
                        log(f"[{device}] acceptPQ")
                        adb_tap(device, *pos2, 3)
                        human_delay()
                        continue
                    continue
                continue
            

        # Crash
        if feature_flags["crash"]:
            pos = find_image(gray, "crashed.png")
            if pos:
                log(f"[{device}] crash")
                adb_tap(device, *pos, 4)
                human_delay()
                continue
            

        # Login
        if feature_flags["login"]:
            pos = find_image(gray, "tapStart.png")
            if pos:
                log(f"[{device}] login")
                adb_tap(device, *pos, 4)
                time.sleep(30)
                continue
            

        time.sleep(0.3)

    active_devices.discard(device)

# ---------------------------
# DEVICE WATCHER
# ---------------------------
def device_watcher():
    global active_devices

    while True:
        # Auto connect LDPlayer
        for port in range(5555, 5565):
            subprocess.run(
                f"adb connect 127.0.0.1:{port}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        devices = get_devices()

        for d in devices:
            if d not in active_devices:
                log(f"[SYSTEM] New device: {d}")
                t = threading.Thread(target=run_bot, args=(d,), daemon=True)
                t.start()
                active_devices.add(d)
                threads[d] = t

        time.sleep(3)

# ---------------------------
# GUI
# ---------------------------
def start_bot():
    global bot_running
    bot_running = True
    status_label.config(text="Status: Running")

def stop_bot():
    global bot_running
    bot_running = False
    status_label.config(text="Status: Stopped")

def create_overlay():
    global status_label, device_listbox, log_widget

    root = tk.Tk()
    root.title("Bot Overlay")
    root.geometry("500x500")
    root.attributes("-topmost", True)

    # -------- Buttons --------
    tk.Button(root, text="Start", command=start_bot, bg="green").pack(pady=5)
    tk.Button(root, text="Stop", command=stop_bot, bg="red").pack(pady=5)

    status_label = tk.Label(root, text="Status: Stopped")
    status_label.pack(pady=5)

    # -------- Device List --------
    tk.Label(root, text="Connected Devices:").pack()

    device_listbox = tk.Listbox(root, height=4)
    device_listbox.pack(fill="both", padx=10, pady=5)

    # -------- Checkboxes (your existing ones) --------
    def make_toggle(name, key):
        var = tk.BooleanVar(value=feature_flags[key])

        def toggle():
            feature_flags[key] = var.get()

        tk.Checkbutton(root, text=name, variable=var, command=toggle).pack(anchor="w")

    make_toggle("NPC Chat", "npc_chat")
    make_toggle("Party DC", "pt_dc")
    make_toggle("Joined Party", "joined_party")
    make_toggle("Invited PQ", "invited_pq")
    make_toggle("Crash Recovery", "crash")
    make_toggle("Auto Login", "login")
    # -------- Log Console --------
    tk.Label(root, text="Logs:").pack()

    log_text = tk.Text(root, height=10)
    log_text.pack(fill="both", padx=10, pady=5)
    log_text.config(state="disabled")
    log_widget = log_text
    # Process log queue
    # def process_log_queue():
    #     while not log_queue.empty():
    #         msg = log_queue.get()

    #         log_widget.config(state="normal")
    #         log_widget.insert(tk.END, msg + "\n")
    #         log_widget.see(tk.END)
    #         log_widget.config(state="disabled")

    #     root.after(100, process_log_queue)

    # process_log_queue()
    # -------- Auto update devices --------
    def update_devices():
        devices = get_devices()

        device_listbox.delete(0, tk.END)

        for d in devices:
            status = "Running" if bot_running else "Idle"
            device_listbox.insert(tk.END, f"{d} [{status}]")

        root.after(2000, update_devices)  # refresh every 2s

    update_devices()

    root.mainloop()

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    log("Starting bot with overlay...")

    watcher = threading.Thread(target=device_watcher, daemon=True)
    watcher.start()

    create_overlay()