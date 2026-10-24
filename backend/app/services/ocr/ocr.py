from __future__ import annotations
import shutil

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None


def ocr_available() -> bool:
    return pytesseract is not None and shutil.which("tesseract") is not None


def preprocess(img):
    """Grayscale, upscale small scans, denoise, binarise. Falls back to plain grayscale without OpenCV."""
    from PIL import Image
    img = img.convert("L")
    try:
        import cv2
        import numpy as np
        a = np.array(img)
        if a.shape[1] < 1600:
            f = 1600 / a.shape[1]
            a = cv2.resize(a, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
        a = cv2.medianBlur(a, 3)
        _, a = cv2.threshold(a, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return Image.fromarray(a)
    except ImportError:
        return img


def fix_rotation(img):
    try:
        osd = pytesseract.image_to_osd(img)
        for line in osd.splitlines():
            if line.startswith("Rotate:"):
                deg = int(line.split(":")[1])
                if deg:
                    return img.rotate(-deg, expand=True)
    except Exception:
        pass  # OSD fails on tiny or blank images; keep the original
    return img


def ocr_image(img):
    """Returns (text, mean_confidence 0-100 or None). Raises RuntimeError when OCR is unavailable."""
    if not ocr_available():
        raise RuntimeError("Tesseract OCR is not installed.")
    img = fix_rotation(preprocess(img))
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, timeout=120)
    confs = []
    for w, c in zip(data["text"], data["conf"]):
        if w.strip():
            try:
                if float(c) >= 0:
                    confs.append(float(c))
            except ValueError:
                pass
    text = pytesseract.image_to_string(img, timeout=120)
    return text, (sum(confs) / len(confs) if confs else None)
