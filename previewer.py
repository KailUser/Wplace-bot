from PIL import Image, ImageDraw
import json

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

def nearest_color_id(rgb):
    best_id, best_dist = 0, float('inf')
    for cid, prgb in PALETTE.items():
        if prgb is None: continue
        dr, dg, db = prgb[0]-rgb[0], prgb[1]-rgb[1], prgb[2]-rgb[2]
        dist = dr*dr + dg*dg + db*db
        if dist < best_dist:
            best_id, best_dist = cid, dist
    return best_id

def parse_ignored_colors(raw_str):
    colors = []
    for p in raw_str.strip().split():
        try:
            r, g, b = map(int, p.split(","))
            colors.append((r, g, b))
        except:
            print(f"⚠️ Skipping invalid color: {p}")
    return colors

def main():
    path = input("🖼 Path to image file (e.g. output.png): ").strip()
    if not path:
        path = "output.png"

    image = Image.open(path).convert("RGBA")
    w, h = image.size
    print(f"📐 Loaded image {w}×{h}")

    raw_ignore = input("🙈 Colors to IGNORE ('R,G,B R,G,B'), or blank: ").strip()
    ignored_colors = parse_ignored_colors(raw_ignore)

    # New image for preview
    preview = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(preview)

    changed_pixels = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = image.getpixel((x, y))
            if a < 128 or (r, g, b) in ignored_colors:
                continue
            cid = nearest_color_id((r, g, b))
            draw.point((x, y), fill=PALETTE[cid])
            changed_pixels += 1

    print(f"🎨 Recolored {changed_pixels} pixels with closest palette colors.")

    out_path = "preview.png"
    preview.save(out_path)
    preview.show()
    print(f"💾 Saved preview as {out_path} ✨")

if __name__ == "__main__":
    main()
