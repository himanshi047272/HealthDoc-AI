from __future__ import annotations
import re
from pathlib import PurePath

ALLOWED = {".pdf": "pdf", ".png": "png", ".jpg": "jpeg", ".jpeg": "jpeg", ".tif": "tiff", ".tiff": "tiff"}
MIMES = {"pdf": {"application/pdf"}, "png": {"image/png"}, "jpeg": {"image/jpeg", "image/jpg"}, "tiff": {"image/tiff"}}


class ValidationError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "invalid_upload"):
        super().__init__(message)
        self.status, self.code = status, code


def safe_filename(name: str) -> str:
    base = PurePath((name or "").replace("\\", "/")).name
    base = re.sub(r"[^\w.\- ]", "_", base).strip(" .")
    return (base or "upload")[:120]


def sniff(data: bytes):
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    return None


def validate_upload(filename: str, content_type: str | None, data: bytes, max_bytes: int) -> tuple[str, str]:
    """Returns (safe_filename, kind). Raises ValidationError."""
    name = safe_filename(filename)
    ext = PurePath(name).suffix.lower()
    if ext not in ALLOWED:
        raise ValidationError(f"Unsupported file type '{ext or 'none'}'. Use PDF, PNG, JPG or TIFF.", 415, "unsupported_type")
    if not data:
        raise ValidationError("The file is empty.", 400, "empty_file")
    if len(data) > max_bytes:
        raise ValidationError(f"File is larger than the {max_bytes // (1024 * 1024)} MB limit.", 413, "too_large")
    kind = sniff(data)
    if kind != ALLOWED[ext]:
        raise ValidationError("File contents do not match its extension.", 415, "signature_mismatch")
    if content_type and content_type not in MIMES[kind] and content_type != "application/octet-stream":
        raise ValidationError(f"MIME type '{content_type}' does not match the file contents.", 415, "mime_mismatch")
    return name, kind
