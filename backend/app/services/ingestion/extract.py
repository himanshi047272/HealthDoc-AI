from __future__ import annotations
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.services.ocr import ocr as ocr_mod


class ProcessingError(Exception):
    """Message is safe to show to the user."""


@dataclass
class PageText:
    page_no: int
    text: str
    source: str  # native | ocr | empty
    ocr_conf: float | None = None


def _native_pages(path: str) -> tuple[list[str], str]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        fitz = None
    try:
        if fitz:
            doc = fitz.open(path)
            if doc.needs_pass:
                raise ProcessingError("The PDF is password-protected. Remove the password and upload it again.")
            return [p.get_text("text") for p in doc], "pymupdf"
        from pypdf import PdfReader
        r = PdfReader(path)
        if r.is_encrypted and not r.decrypt(""):
            raise ProcessingError("The PDF is password-protected. Remove the password and upload it again.")
        return [(p.extract_text() or "") for p in r.pages], "pypdf"
    except ProcessingError:
        raise
    except Exception:
        raise ProcessingError("The PDF could not be read. It may be damaged or not a valid PDF.")


def _rasterize(path: str, page_no: int, dpi: int = 200):
    from PIL import Image
    try:
        import fitz
        pix = fitz.open(path)[page_no - 1].get_pixmap(dpi=dpi)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    except ImportError:
        pass
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(page_no), "-l", str(page_no), "-png", path, f"{d}/p"],
                       check=True, timeout=90, capture_output=True)
        img = Image.open(sorted(Path(d).glob("p*.png"))[0])
        img.load()
        return img


def extract_pdf(path: str, settings) -> tuple[list[PageText], str]:
    raw, extractor = _native_pages(path)
    if not raw:
        raise ProcessingError("The PDF has no pages.")
    if len(raw) > settings.max_pages:
        raise ProcessingError(f"The PDF has {len(raw)} pages; the limit is {settings.max_pages}.")
    pages, ocr_ok = [], settings.ocr_enabled and ocr_mod.ocr_available()
    for i, text in enumerate(raw, 1):
        if len(text.strip()) >= settings.min_page_chars:
            pages.append(PageText(i, text, "native"))
        elif ocr_ok:
            try:
                t, conf = ocr_mod.ocr_image(_rasterize(path, i))
                pages.append(PageText(i, t, "ocr" if t.strip() else "empty", conf))
            except Exception:
                pages.append(PageText(i, "", "empty"))  # OCR failure is recorded, not hidden
        else:
            pages.append(PageText(i, text, "native" if text.strip() else "empty"))
    return pages, extractor


def extract_image(path: str, settings) -> tuple[list[PageText], str]:
    from PIL import Image, ImageSequence
    if not (settings.ocr_enabled and ocr_mod.ocr_available()):
        raise ProcessingError("OCR is not available, so images cannot be read. Install Tesseract (see Settings).")
    try:
        img = Image.open(path)
        frames = [f.copy() for f in ImageSequence.Iterator(img)][: settings.max_pages]
    except Exception:
        raise ProcessingError("The image could not be opened. It may be damaged.")
    pages = []
    for i, f in enumerate(frames, 1):
        try:
            t, conf = ocr_mod.ocr_image(f)
            pages.append(PageText(i, t, "ocr" if t.strip() else "empty", conf))
        except Exception:
            pages.append(PageText(i, "", "empty"))
    return pages, "tesseract"
