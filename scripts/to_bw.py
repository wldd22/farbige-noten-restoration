import os
from PIL import Image

# ==========================
# USER CONFIGURATION
# ==========================

INPUT_ROOT = "working/png-scans/part-1/temp"
OUTPUT_ROOT = "working/bw-scans/part-1"

ENABLE_GRAYSCALE = True

# White balance multipliers
WB_R = 1.25
WB_G = 1.0
WB_B = 1.1

# Contrast: 0.0–5.0 (≈5.0 ≈ pure B/W)
CONTRAST = 5.0

# ==========================
# FILTER
# ==========================

def apply_filter(img,
                 grayscale=True,
                 wb_r=1.0,
                 wb_g=1.0,
                 wb_b=1.0,
                 contrast=1.0):
    img = img.convert("RGB")

    # Step 1: Grayscale
    if grayscale:
        img = img.convert("L").convert("RGB")

    # Step 2: White balance
    r, g, b = img.split()
    r = r.point(lambda i: min(255, int(i * wb_r)))
    g = g.point(lambda i: min(255, int(i * wb_g)))
    b = b.point(lambda i: min(255, int(i * wb_b)))
    img = Image.merge("RGB", (r, g, b))

    # Step 3: Contrast (grayscale domain)
    gray = img.convert("L")

    table = [
        max(0, min(255, int(128 + (i - 128) * contrast)))
        for i in range(256)
    ]

    gray = gray.point(table)
    img = gray.convert("RGB")

    return img

# ==========================
# PROCESS DIRECTORY TREE
# ==========================

for root, _, files in os.walk(INPUT_ROOT):
    for file in files:
        if not file.lower().endswith(".png"):
            continue

        input_path = os.path.join(root, file)
        rel = os.path.relpath(root, INPUT_ROOT)
        out_dir = os.path.join(OUTPUT_ROOT, rel)
        os.makedirs(out_dir, exist_ok=True)

        with Image.open(input_path) as img:
            result = apply_filter(
                img,
                grayscale=ENABLE_GRAYSCALE,
                wb_r=WB_R,
                wb_g=WB_G,
                wb_b=WB_B,
                contrast=CONTRAST
            )
            result.save(os.path.join(out_dir, file))

print("Processing complete.")
