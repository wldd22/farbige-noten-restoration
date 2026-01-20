# to_bw.py
import os
from PIL import Image

# ==========================
# USER CONFIGURATION
# ==========================

INPUT_ROOT = "working\\png-scans"
OUTPUT_ROOT = "working\\bw-scans"

ENABLE_GRAYSCALE = True

# White balance configuration
WB_CONFIG = {
    "default": {
        "wb_r": 0.8,
        "wb_g": 0.6,
        "wb_b": 1.8
    },
    "exceptions": [
        {
            "wb_r": 1.2,
            "wb_g": 0.8,
            "wb_b": 1.6,
            "file_names": "FN-PG-P1-27.png"
        },
        {
            "wb_r": 1.0,
            "wb_g": 0.6,
            "wb_b": 1.4,
            "file_names": "FN-PG-P2-01.png"
        },
        {
            "wb_r": 0.8,
            "wb_g": 1.2,
            "wb_b": 2.2,
            "file_names": "FN-PG-P2-56.png"
        },
        {
            "wb_r": 0.8,
            "wb_g": 1.2,
            "wb_b": 0.4,
            "file_names": ["FN-PG-P3-01.png", "FN-PG-P3-02.png", "FN-PG-P3-03.png"]
        }
    ]
}

# Contrast: 0.0–5.0 (≈5.0 ≈ pure B/W)
CONTRAST = 5.0

VERBOSE = False  # Set to False to reduce console output

# ==========================
# HELPERS
# ==========================

def _normalize_path(p):
    """Normalize path for comparison (use forward slashes, lowercased)."""
    return os.path.normpath(p).replace(os.sep, "/").lower()

def get_wb_for_file(basename, relpath):
    """
    Return (wb_r, wb_g, wb_b) for the given filename.
    Matches exceptions by basename OR by relative path (both case-insensitive).
    If multiple exceptions match, the first matching exception is used.
    """
    default = WB_CONFIG.get("default", {})
    wb_r = default.get("wb_r", 1.0)
    wb_g = default.get("wb_g", 1.0)
    wb_b = default.get("wb_b", 1.0)

    exceptions = WB_CONFIG.get("exceptions", [])
    norm_basename = _normalize_path(basename)
    norm_rel = _normalize_path(relpath) if relpath else ""

    for exc in exceptions:
        names = exc.get("file_names") or exc.get("file_names".lower()) or []
        # allow either a single string or an iterable
        if isinstance(names, str):
            names = [names]
        # Normalize each name and compare against basename and relative path
        for n in names:
            norm_n = _normalize_path(n)
            if norm_n == norm_basename or norm_n == norm_rel:
                return (
                    exc.get("wb_r", wb_r),
                    exc.get("wb_g", wb_g),
                    exc.get("wb_b", wb_b),
                )
    return (wb_r, wb_g, wb_b)

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

processed = 0
skipped = 0

for root, _, files in os.walk(INPUT_ROOT):
    for file in files:
        if not file.lower().endswith(".png"):
            skipped += 1
            continue

        input_path = os.path.join(root, file)
        rel = os.path.relpath(root, INPUT_ROOT)
        # If file is directly at INPUT_ROOT, rel will be '.'. Normalize to ''
        rel = "" if rel == "." else rel
        out_dir = os.path.join(OUTPUT_ROOT, rel)
        os.makedirs(out_dir, exist_ok=True)

        # Determine white balance multipliers for this file
        # Compare both basename and relative path (rel + '/' + file)
        rel_path_with_file = os.path.join(rel, file) if rel else file
        wb_r, wb_g, wb_b = get_wb_for_file(file, rel_path_with_file)

        print(f"Processing: {input_path}")

        if VERBOSE:
            print(f"  -> Output dir: {out_dir}")
            print(f"  -> WB multipliers: R={wb_r}, G={wb_g}, B={wb_b}")
            print(f"  -> Contrast: {CONTRAST}, Grayscale: {ENABLE_GRAYSCALE}")

        with Image.open(input_path) as img:
            result = apply_filter(
                img,
                grayscale=ENABLE_GRAYSCALE,
                wb_r=wb_r,
                wb_g=wb_g,
                wb_b=wb_b,
                contrast=CONTRAST
            )
            out_path = os.path.join(out_dir, file)
            result.save(out_path)
            processed += 1

if VERBOSE:
    print(f"\nProcessing complete. {processed} files processed, {skipped} non-PNG files skipped.")
else:
    print("Processing complete.")
