"""
batch_ocr_prompt.py

Interactive batch OCR for PNGs (and configurable extensions) using pytesseract.
For each image under a root folder (default: ./pngs) it writes a transcript to a mirrored
path under an output root (default: ./transcripts). e.g.:
  pngs/path/to/img-001.png -> transcripts/path/to/img-001.txt

Dependencies:
    pip install pytesseract pillow

Optional (recommended):
    pip install opencv-python numpy tqdm

Make sure Tesseract OCR is installed and accessible (or supply its full path when prompted).
"""
from pathlib import Path
import sys
import logging
import textwrap

from PIL import Image, UnidentifiedImageError
import pytesseract

# Optional libraries
try:
    import cv2
    import numpy as np
    HAVE_CV2 = True
except Exception:
    HAVE_CV2 = False

try:
    from tqdm import tqdm
    HAVE_TQDM = True
except Exception:
    HAVE_TQDM = False


def prompt_with_default(prompt: str, default: str) -> str:
    prompt_full = f"{prompt} [{default}]: "
    resp = input(prompt_full).strip()
    return resp if resp != "" else default


def prompt_choice(prompt: str, choices, default):
    choices_str = "/".join(str(c) for c in choices)
    while True:
        resp = input(f"{prompt} ({choices_str}) [{default}]: ").strip()
        if resp == "":
            return default
        if resp in choices:
            return resp
        print(f"Invalid choice. Choose one of: {choices_str}")


def prompt_int(prompt: str, default: int, min_val=None, max_val=None):
    while True:
        resp = input(f"{prompt} [{default}]: ").strip()
        if resp == "":
            return default
        try:
            v = int(resp)
            if (min_val is not None and v < min_val) or (max_val is not None and v > max_val):
                print(f"Value must be between {min_val} and {max_val}.")
                continue
            return v
        except ValueError:
            print("Enter a valid integer.")


def prompt_yes_no(prompt: str, default_yes=True) -> bool:
    default = "Y/n" if default_yes else "y/N"
    while True:
        resp = input(f"{prompt} [{default}]: ").strip().lower()
        if resp == "" :
            return default_yes
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("Please answer yes or no (y/n).")


def ensure_tesseract_available():
    try:
        _ = pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


# Image preprocessing helpers (same as previous script)
def upscale_image_pil(img: Image.Image, factor: int) -> Image.Image:
    if factor <= 1:
        return img
    w, h = img.size
    return img.resize((w * factor, h * factor), resample=Image.Resampling.LANCZOS)


def pil_to_cv(img: Image.Image):
    arr = np.array(img)
    if arr.ndim == 2:
        return arr
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def cv_to_pil(arr):
    if arr.ndim == 2:
        return Image.fromarray(arr)
    arr_rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(arr_rgb)


def deskew_cv(img_pil: Image.Image) -> Image.Image:
    if not HAVE_CV2:
        logging.debug("OpenCV not available; skipping deskew.")
        return img_pil
    try:
        gray = pil_to_cv(img_pil if img_pil.mode == 'L' else img_pil.convert('L'))
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(bw < 255))
        if coords.shape[0] < 10:
            logging.debug("Not enough text pixels for reliable deskew; skipping deskew.")
            return img_pil
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(pil_to_cv(img_pil), M, (w, h),
                                 flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return cv_to_pil(rotated)
    except Exception as e:
        logging.debug("Deskew failed: %s", e)
        return img_pil


def threshold_pil(img_pil: Image.Image) -> Image.Image:
    gray = img_pil.convert('L')
    if HAVE_CV2:
        arr = np.array(gray)
        try:
            _, th = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return Image.fromarray(th)
        except Exception as e:
            logging.debug("OpenCV threshold failed: %s", e)
    return gray.point(lambda p: 255 if p > 128 else 0) # type: ignore


def preprocess_image(img_path: Path, method: str = 'thresh', upscale: int = 1) -> Image.Image:
    img = Image.open(img_path)
    if img.mode not in ('L', 'RGB', 'RGBA'):
        img = img.convert('RGB')
    if upscale > 1:
        img = upscale_image_pil(img, upscale)
    if method == 'none':
        return img
    if method == 'thresh':
        return threshold_pil(img)
    if method == 'deskew':
        return deskew_cv(img)
    if method in ('thresh+deskew', 'deskew+thresh'):
        d = deskew_cv(img)
        return threshold_pil(d)
    return img


def gather_images(root: Path, extensions):
    exts = {e.lower() if e.startswith('.') else f'.{e.lower()}' for e in extensions}
    files = [p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in exts]
    files.sort()
    return files


def interactive_config():
    print(textwrap.dedent("""
    Interactive setup for batch OCR.
    Press Enter to accept the default shown in [brackets].
    """).strip())
    # Root input folder
    while True:
        png_root = Path(prompt_with_default("Root folder containing images", "working/bw-scans")).expanduser().resolve()
        if png_root.exists() and png_root.is_dir():
            break
        create = prompt_yes_no(f"Folder '{png_root}' does not exist. Create it?", default_yes=False)
        if create:
            try:
                png_root.mkdir(parents=True, exist_ok=True)
                print(f"Created folder: {png_root}")
                break
            except Exception as e:
                print(f"Failed to create folder: {e}")
        else:
            print("Please enter an existing folder path.")
    # Output root
    out_root = Path(prompt_with_default("Output folder for transcripts", "transcriptions/ocr")).expanduser().resolve()
    if not out_root.exists():
        create = prompt_yes_no(f"Output folder '{out_root}' does not exist. Create it?", default_yes=True)
        if create:
            try:
                out_root.mkdir(parents=True, exist_ok=True)
                print(f"Created folder: {out_root}")
            except Exception as e:
                print(f"Failed to create folder: {e}")
        else:
            print("Transcripts will be created when needed (parent folders will be made).")

    # Extensions
    exts_raw = prompt_with_default("File extensions to include (comma-separated)", ".png")
    exts = [x.strip().lower() for x in exts_raw.split(",") if x.strip() != ""]
    if not exts:
        exts = ['.png']

    # Language
    lang = prompt_with_default("Tesseract language(s)", "deu")

    # Extra config string
    config = prompt_with_default("Extra Tesseract config string (--psm, --oem, -c ...)", "")

    # Preprocess choices
    preprocess_choices = ['none', 'thresh', 'deskew', 'thresh+deskew']
    preprocess = prompt_choice("Preprocessing method", preprocess_choices, 'thresh')

    # Upscale
    upscale = prompt_int("Integer upscale factor (1 = none, 2 or 3 helpful for small scans)", 1, min_val=1, max_val=10)

    # Test-first mode
    test_first = prompt_yes_no("Test-first mode: only process the first image found?", default_yes=False)

    # Verbose
    verbose = prompt_yes_no("Verbose logging?", default_yes=False)

    # Tesseract availability
    if not ensure_tesseract_available():
        print("Tesseract not found on PATH (pytesseract cannot locate it).")
        give_path = prompt_yes_no("Would you like to provide the full path to the tesseract executable now?", default_yes=True)
        if give_path:
            while True:
                candidate = input("Enter full path to tesseract executable (or blank to skip): ").strip()
                if candidate == "":
                    break
                p = Path(candidate)
                if p.exists():
                    pytesseract.pytesseract.tesseract_cmd = str(p)
                    if ensure_tesseract_available():
                        print("Tesseract path set and verified.")
                        break
                    else:
                        print("That path did not make pytesseract find tesseract. Try again or leave blank to skip.")
                else:
                    print("Path does not exist, try again.")
        else:
            print("Proceeding without setting tesseract path. If Tesseract is not installed or not on PATH, OCR will fail.")

    summary = {
        'png_root': png_root,
        'out_root': out_root,
        'extensions': exts,
        'lang': lang,
        'config': config,
        'preprocess': preprocess,
        'upscale': upscale,
        'test_first': test_first,
        'verbose': verbose
    }

    print("\nConfiguration summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    proceed = prompt_yes_no("Proceed with OCR using the above settings?", default_yes=True)
    if not proceed:
        print("Aborted by user.")
        sys.exit(0)
    return summary


def main():
    cfg = interactive_config()
    logging.basicConfig(level=logging.DEBUG if cfg['verbose'] else logging.INFO,
                        format='%(levelname)s: %(message)s')

    images = gather_images(cfg['png_root'], cfg['extensions'])
    if not images:
        logging.info("No images found under %s with extensions %s", cfg['png_root'], cfg['extensions'])
        return

    iterable = images
    if HAVE_TQDM and not cfg['test_first']:
        iterable = tqdm(images, desc="OCR images", unit="img")

    processed = 0
    for idx, img_path in enumerate(iterable):
        if cfg['test_first'] and idx > 0:
            break
        try:
            rel = img_path.relative_to(cfg['png_root'])
        except Exception:
            # fallback: use name only
            rel = img_path.name
        out_path = (cfg['out_root'] / rel).with_suffix('.txt')
        out_path.parent.mkdir(parents=True, exist_ok=True)

        logging.info("Processing: %s -> %s", img_path, out_path)
        try:
            pre = preprocess_image(img_path, method=cfg['preprocess'], upscale=cfg['upscale'])
            text = pytesseract.image_to_string(pre, lang=cfg['lang'], config=cfg['config'])
            out_path.write_text(text, encoding='utf-8')
            processed += 1
        except UnidentifiedImageError:
            logging.error("File is not a recognized image: %s", img_path)
        except pytesseract.TesseractError as te:
            logging.error("Tesseract error processing %s: %s", img_path, te)
        except Exception as e:
            logging.error("Failed to OCR %s: %s", img_path, e)

        if cfg['test_first']:
            logging.info("Test-first mode: processed first image only.")
            break

    logging.info("Done. Processed %d image(s). Transcripts are under: %s", processed, cfg['out_root'])


if __name__ == '__main__':
    main()
