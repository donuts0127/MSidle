<<<<<<< HEAD
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
# FAST SCREENSHOT (MEMORY)
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
    print(f"adb_tap", jx, jy)
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
    print(f"[{device}] Bot started...")

    while True:
        # Check if device still alive
        if device not in get_devices():
            print(f"[{device}] DISCONNECTED → stopping thread")
            break

        img = adb_screencap(device)

        if img is None:
            print(f"[{device}] Screencap failed → stopping thread")
            break

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Priority 1: Close popups
        pos = find_image(gray, "npcChat.png")
        if pos:
            print(f"[{device}] npcChat", pos)
            adb_tap(device, *pos, jitter_amount=5)
            human_delay()
            continue

        # Priority 2: ptStopped
        pos = find_image(gray, "ptStopped.png")
        if pos:
            #print(f"[{device}] ptStopped", pos)

            pos2 = find_image(gray, "ptDC.png")
            if pos2:
                print(f"[{device}] ptDC", pos2)
                adb_tap(device, *pos2, jitter_amount=7)
                human_delay()
                continue
            continue

        # Priority 3: joinedParty
        pos = find_image(gray, "joinedParty.png")
        if pos:
            #print(f"[{device}] joinedParty", pos)

            x, y = 520, 360
            if y < img.shape[0] and x < img.shape[1]:
                b, g, r = img[y, x]
                if r > 150 and g > 150 and b < 100:  # Check if the button is yellow
                    pos3 = find_image(gray, "enterPQ.png")
                    b1, g1, r1 = img[pos3[1]+6, pos3[0]+6]
                    if b1 > r1 and b1 > g1:  # Check if the button is blue
                        print(f"[{device}] enterPQ", pos3)
                        adb_tap(device, *pos3, jitter_amount=9)
                        human_delay()
                        continue
            continue

        # Priority 4: invitedPQ
        pos = find_image(gray, "invitedPQ.png")
        if pos:
            #print(f"[{device}] invitedPQ", pos)

            pos2 = find_image(gray, "acceptPQ.png")
            b, g, r = img[pos2[1], pos2[0]]
            if b > r and b > g:  # Check if the button is blue
                print(f"[{device}] acceptPQ", pos2)
                adb_tap(device, *pos2, jitter_amount=3)
                human_delay()
                continue
            continue



        # If Crash Launch back
        pos = find_image(gray, "crashed.png")
        if pos:
            print(f"[{device}] Crash detected", pos)
            adb_tap(device, *pos, jitter_amount=4)
            human_delay()
            continue

        # Login after crash
        pos = find_image(gray, "tapStart.png")
        if pos:
            print(f"[{device}] Crash detected", pos)
            adb_tap(device, *pos, jitter_amount=4)
            time.sleep(120)  # Wait for game to load
            continue
            
        # skip offline reward screen
        pos = find_image(gray, "offlineReward.png")
        if pos:
            pos2 = find_image(gray, "offlineRewardOk.png")
            b, g, r = img[pos2[1], pos2[0]]
            if b >r and b > g:  # Check if the button is blue
                print(f"[{device}] OfflineReward", pos2)
                adb_tap(device, *pos2, jitter_amount=7)
                human_delay()
                continue
            continue

        # skip notice screen
        pos = find_image(gray, "startPopup.png")
        if pos:
            pos2 = find_image(gray, "startPopupClose.png")
            if pos2: 
                print(f"[{device}] Notice close", pos2)
                adb_tap(device, *pos2, jitter_amount=7)
                human_delay()
                continue
            continue

        time.sleep(0.3)

    active_devices.discard(device)
    print(f"[{device}] Thread exited")

# ---------------------------
# DEVICE WATCHER
# ---------------------------
def device_watcher():
    global active_devices

    while True:
        # Auto-connect LDPlayer ports
        for port in range(5555, 5565):
            subprocess.run(
                f"adb connect 127.0.0.1:{port}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

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
    print("Starting ultra-fast multi-instance bot...")

    watcher = threading.Thread(target=device_watcher, daemon=True)
    watcher.start()

    while True:
=======
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
# FAST SCREENSHOT (MEMORY)
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
    print(f"adb_tap", jx, jy)
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
    print(f"[{device}] Bot started...")

    while True:
        # Check if device still alive
        if device not in get_devices():
            print(f"[{device}] DISCONNECTED → stopping thread")
            break

        img = adb_screencap(device)

        if img is None:
            print(f"[{device}] Screencap failed → stopping thread")
            break

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Priority 1: Close popups
        pos = find_image(gray, "npcChat.png")
        if pos:
            print(f"[{device}] npcChat", pos)
            adb_tap(device, *pos, jitter_amount=5)
            human_delay()
            continue

        # Priority 2: ptStopped
        pos = find_image(gray, "ptStopped.png")
        if pos:
            #print(f"[{device}] ptStopped", pos)

            pos2 = find_image(gray, "ptDC.png")
            if pos2:
                print(f"[{device}] ptDC", pos2)
                adb_tap(device, *pos2, jitter_amount=7)
                human_delay()
                continue
            continue

        # Priority 3: joinedParty
        pos = find_image(gray, "joinedParty.png")
        if pos:
            #print(f"[{device}] joinedParty", pos)

            x, y = 520, 360
            if y < img.shape[0] and x < img.shape[1]:
                b, g, r = img[y, x]
                if r > 150 and g > 150 and b < 100:  # Check if the button is yellow
                    pos3 = find_image(gray, "enterPQ.png")
                    b1, g1, r1 = img[pos3[1]+6, pos3[0]+6]
                    if b1 > r1 and b1 > g1:  # Check if the button is blue
                        print(f"[{device}] enterPQ", pos3)
                        adb_tap(device, *pos3, jitter_amount=9)
                        human_delay()
                        continue
            continue

        # Priority 4: invitedPQ
        pos = find_image(gray, "invitedPQ.png")
        if pos:
            #print(f"[{device}] invitedPQ", pos)

            pos2 = find_image(gray, "acceptPQ.png")
            b, g, r = img[pos2[1], pos2[0]]
            if b > r and b > g:  # Check if the button is blue
                print(f"[{device}] acceptPQ", pos2)
                adb_tap(device, *pos2, jitter_amount=3)
                human_delay()
                continue
            continue



        # If Crash Launch back
        pos = find_image(gray, "crashed.png")
        if pos:
            print(f"[{device}] Crash detected", pos)
            adb_tap(device, *pos, jitter_amount=4)
            human_delay()
            continue

        # Login after crash
        pos = find_image(gray, "tapStart.png")
        if pos:
            print(f"[{device}] Crash detected", pos)
            adb_tap(device, *pos, jitter_amount=4)
            time.sleep(120)  # Wait for game to load
            continue
            
        # skip offline reward screen
        pos = find_image(gray, "offlineReward.png")
        if pos:
            pos2 = find_image(gray, "offlineRewardOk.png")
            b, g, r = img[pos2[1], pos2[0]]
            if b >r and b > g:  # Check if the button is blue
                print(f"[{device}] OfflineReward", pos2)
                adb_tap(device, *pos2, jitter_amount=7)
                human_delay()
                continue
            continue

        # skip notice screen
        pos = find_image(gray, "startPopup.png")
        if pos:
            pos2 = find_image(gray, "startPopupClose.png")
            if pos2: 
                print(f"[{device}] Notice close", pos2)
                adb_tap(device, *pos2, jitter_amount=7)
                human_delay()
                continue
            continue

        time.sleep(0.3)

    active_devices.discard(device)
    print(f"[{device}] Thread exited")

# ---------------------------
# DEVICE WATCHER
# ---------------------------
def device_watcher():
    global active_devices

    while True:
        # Auto-connect LDPlayer ports
        for port in range(5555, 5565):
            subprocess.run(
                f"adb connect 127.0.0.1:{port}",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

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
    print("Starting ultra-fast multi-instance bot...")

    watcher = threading.Thread(target=device_watcher, daemon=True)
    watcher.start()

    while True:
>>>>>>> 17cf502363b9fb16fb06a87a3a5bebf1e2940c24
        time.sleep(10)