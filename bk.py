import cv2
import numpy as np
import time
import random
import subprocess
import os
import threading
from config import *

ASSETS_PATH = "assets"

# ---------------------------
# GLOBAL STATE
# ---------------------------
active_devices = set()
threads = {}

# ---------------------------
# GET DEVICES
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

            # ✅ ONLY allow LDPlayer (127.0.0.1:PORT)
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
# ADB FUNCTIONS
# ---------------------------
def adb_cmd(device, cmd):
    return f"adb -s {device} {cmd}"

def adb_screencap(device):
    ok = safe_run(adb_cmd(device, "shell screencap -p /sdcard/screen.png"))
    if not ok:
        return False

    ok = safe_run(adb_cmd(device, f"pull /sdcard/screen.png screen_{device}.png"))
    return ok

def adb_tap(device, x, y):
    return safe_run(adb_cmd(device, f"shell input tap {x} {y}"))

# ---------------------------
# IMAGE DETECTION
# ---------------------------
def find_image(device, template_name):
    screen_path = f"screen_{device}.png"
    template_path = os.path.join(ASSETS_PATH, template_name)

    screen = cv2.imread(screen_path, 0)
    template = cv2.imread(template_path, 0)

    if screen is None or template is None:
        return None

    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
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
    print(f"[{device}] Bot started...")

    while True:
        # Check if device still alive
        if device not in get_devices():
            print(f"[{device}] DISCONNECTED → stopping thread")
            break

        if not adb_screencap(device):
            print(f"[{device}] Screencap failed → stopping thread")
            break

        screen_path = f"screen_{device}.png"
        img = cv2.imread(screen_path)

        # Priority 1: Close popups
        pos = find_image(device, "npcChat.png")
        if pos:
            print(f"[{device}] npcChat", pos)
            adb_tap(device, *pos)
            human_delay()
            continue

        # Priority 2: ptStopped
        pos = find_image(device, "ptStopped.png")
        if pos:
            print(f"[{device}] ptStopped", pos)

            pos2 = find_image(device, "ptDC.png")
            if pos2:
                print(f"[{device}] ptDC", pos2)
                adb_tap(device, *pos2)
                human_delay()
                continue
            continue

        # Priority 3: joinedParty
        pos = find_image(device, "joinedParty.png")
        if pos:
            print(f"[{device}] joinedParty", pos)

            if img is not None:
                x, y = 520, 360
                b, g, r = img[y, x]
                brightness = (r + g + b) / 3

                if brightness < 15:
                    pos3 = find_image(device, "enterPQ.png")
                    if pos3:
                        print(f"[{device}] enterPQ", pos3)
                        adb_tap(device, *pos3)
                        human_delay()
                        continue
            continue

        # Priority 4: invitedPQ
        pos = find_image(device, "invitedPQ.png")
        if pos:
            print(f"[{device}] invitedPQ", pos)

            pos2 = find_image(device, "acceptPQ.png")
            if pos2:
                print(f"[{device}] acceptPQ", pos2)
                adb_tap(device, *pos2)
                human_delay()
                continue
            continue

        time.sleep(1)

    # Remove from active list when done
    active_devices.discard(device)
    print(f"[{device}] Thread exited")

# ---------------------------
# DEVICE WATCHER
# ---------------------------
def device_watcher():
    global active_devices

    while True:
        # Try auto-connect common LDPlayer ports
        for port in range(5555, 5565):
            subprocess.run(f"adb connect 127.0.0.1:{port}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        devices = get_devices()

        # Add new devices
        for d in devices:
            if d not in active_devices:
                print(f"[SYSTEM] New device detected: {d}")

                t = threading.Thread(target=run_bot, args=(d,), daemon=True)
                t.start()

                active_devices.add(d)
                threads[d] = t

        # Remove dead devices
        for d in list(active_devices):
            if d not in devices:
                print(f"[SYSTEM] Device removed: {d}")
                active_devices.remove(d)

        time.sleep(3)

# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    print("Starting multi-instance bot with auto-detect...")

    watcher = threading.Thread(target=device_watcher, daemon=True)
    watcher.start()

    # Keep main alive
    while True:
        time.sleep(10)