import json
import os
import time
import requests
from PIL import Image

# 32-color palette (ID → RGB)
PALETTE = {
    0:  None,
    1:  (0,0,0),    2:(60,60,60),   3:(120,120,120),  4:(210,210,210),
    5:(255,255,255),6:(96,0,24),    7:(237,28,36),    8:(255,127,39),
    9:(246,170,9), 10:(249,221,59),11:(255,250,188), 12:(14,185,104),
   13:(19,230,123),14:(135,255,94),15:(12,129,110),  16:(16,174,166),
   17:(19,225,190),18:(40,80,158), 19:(64,147,228),  20:(96,247,242),
   21:(107,80,246),22:(153,177,251),23:(120,12,153),24:(170,56,185),
   25:(224,159,249),26:(203,0,122),27:(236,31,128),28:(243,141,169),
   29:(104,70,52), 30:(149,104,42),31:(248,178,119),
}

PROGRESS_FILE = "progress.json"

def nearest_color_id(rgb):
    best_id, best_dist = 0, float('inf')
    for cid, prgb in PALETTE.items():
        if prgb is None: continue
        dr, dg, db = prgb[0]-rgb[0], prgb[1]-rgb[1], prgb[2]-rgb[2]
        dist = dr*dr + dg*dg + db*db
        if dist < best_dist:
            best_id, best_dist = cid, dist
    return best_id

def rel_coord(n):
    return n % 1000

def load_settings(path="settings.json"):
    with open(path, "r") as f:
        return json.load(f)

def chunked_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]

def parse_ignored_colors(raw_str):
    colors = []
    for p in raw_str.strip().split():
        try:
            r, g, b = map(int, p.split(","))
            colors.append((r, g, b))
        except:
            print(f"⚠️ Skipping invalid color: {p}")
    return colors

def fetch_user_charges(headers, cookies):
    resp = requests.get("https://backend.wplace.live/me", headers=headers, cookies=cookies)
    resp.raise_for_status()
    ch = resp.json()["charges"]
    return ch["count"], ch["max"], ch["cooldownMs"] / 1000.0

def save_progress(idx):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"batch_index": idx}, f)

def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return None
    with open(PROGRESS_FILE, "r") as f:
        return json.load(f).get("batch_index", 0)

def clear_progress():
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

def main():
    settings = load_settings()
    cookies = {"s": settings["s"]}
    if settings.get("cf_clearance"):
        cookies["cf_clearance"] = settings["cf_clearance"]
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
        "Accept": "*/*",
        "Referer": "https://wplace.live/",
        "Origin": "https://wplace.live",
    }

    print("🔥 Image-to-Pixels Drawer (with resume support) 🔥\n")

    # Fetch live charges
    current_charges, max_charges, regen_interval = fetch_user_charges(headers, cookies)
    regen_rate = 1.0 / regen_interval
    print(f"💧 Charges: {current_charges:.2f}/{max_charges}, Regen: 1 per {regen_interval:.0f}s\n")

    # Chunk & offsets
    primary = int(input("Primary chunk X (e.g. 139): ").strip())
    sub     = int(input("Sub-chunk Y    (e.g. 910): ").strip())
    start_x = int(input("Start offset X inside chunk (0–999): ").strip())
    start_y = int(input("Start offset Y inside chunk (0–999): ").strip())

    # Load image
    path = input("\nPath to image file: ").strip()
    # path = 'output.png'
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    print(f" → Loaded image {w}×{h}")

    # Ignored colors
    raw_ignore = input("Colors to IGNORE ('R,G,B R,G,B'), or blank: ").strip()
    ignored_colors = parse_ignored_colors(raw_ignore)
    if ignored_colors:
        print(f" → Ignoring: {ignored_colors}\n")
    else:
        print(" → No ignored colors.\n")

    # Build full coord/color lists
    all_coords, all_colors = [], []
    for y in range(h):
        for x in range(w):
            r, g, b, a = img.getpixel((x, y))
            if a < 128 or (r, g, b) in ignored_colors:
                continue
            cid = nearest_color_id((r, g, b))
            abs_x = primary*1000 + start_x + x
            abs_y = sub    *1000 + start_y + y
            all_coords += [rel_coord(abs_x), rel_coord(abs_y)]
            all_colors.append(cid)

    total_pixels = len(all_colors)
    if total_pixels == 0:
        print("❗️ Nothing to draw.")
        return

    # Prepare batches
    BATCH_SIZE = 16
    coord_batches = list(chunked_list(all_coords, 2 * BATCH_SIZE))
    color_batches = list(chunked_list(all_colors, BATCH_SIZE))
    num_batches = len(color_batches)

    # Check for resume
    resume_idx = load_progress()
    if resume_idx is not None and 0 <= resume_idx < num_batches:
        ans = input(f"Found saved progress at batch {resume_idx}/{num_batches}. Resume? (Y/n): ").strip().lower()
        if ans in ("", "y", "yes"):
            start_batch = resume_idx
            print(f"→ Resuming from batch {start_batch}\n")
        else:
            start_batch = 0
            clear_progress()
    else:
        start_batch = 0

    url = f"https://backend.wplace.live/s0/pixel/{primary}/{sub}"
    last_time = time.time()
    pixels_drawn = start_batch * BATCH_SIZE

    # Drawing loop
    for idx in range(start_batch, num_batches):
        coord_batch = coord_batches[idx]
        color_batch = color_batches[idx]
        needed = len(color_batch)

        # Regen
        now = time.time()
        elapsed = now - last_time
        current_charges = min(max_charges, current_charges + regen_rate * elapsed)
        last_time = now

        # Wait if needed
        if current_charges < needed:
            deficit = needed - current_charges
            wait_sec = deficit * regen_interval
            waited = 0
            print(f"⏱ Batch {idx}: need {deficit:.2f} charges → waiting {wait_sec:.1f}s")
            while waited < wait_sec:
                step = min(10, wait_sec - waited)
                time.sleep(step)
                waited += step
                print(f"   ⌛ Waited {waited:.1f}/{wait_sec:.1f}s")
            current_charges = min(max_charges, current_charges + regen_rate * wait_sec)
            last_time = time.time()

        # Send
        payload = json.dumps({"coords": coord_batch, "colors": color_batch})
        resp = requests.post(url, headers=headers, cookies=cookies, data=payload)
        if resp.status_code == 403:
            time.sleep(1)
            resp = requests.post(url, headers=headers, cookies=cookies, data=payload)

        # Sync charges
        try:
            ch = resp.json().get("charges")
            if ch:
                current_charges = float(ch["count"])
                max_charges = float(ch["max"])
        except:
            pass

        pixels_drawn += needed
        current_charges -= needed
        print(f"[{pixels_drawn}/{total_pixels}] ✔ batch {idx+1}/{num_batches}, HTTP {resp.status_code}, charges {current_charges:.2f}/{max_charges}")

        # Save progress
        save_progress(idx + 1)

    # Done
    clear_progress()
    print("\n✅ Completed all batches. Progress cleared. 🚀")

if __name__ == "__main__":
    main()
