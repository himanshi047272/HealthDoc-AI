import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.core.config import load_settings
from app.services.app_service import HealthDocService

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def make_pdf(pages: list[str]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=0)
    for t in pages:
        y = 700
        for line in t.split("\n"):
            c.drawString(72, y, line); y -= 16
        c.showPage()
    c.save()
    return buf.getvalue()


def text_image(text: str, rotate=0) -> "Image":
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1400, 500), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 38)
    for i, line in enumerate(text.split("\n")):
        d.text((50, 50 + i * 60), line, fill="black", font=f)
    return img.rotate(rotate, expand=True) if rotate else img


def png_bytes(img) -> bytes:
    b = io.BytesIO(); img.save(b, "PNG"); return b.getvalue()


class ServiceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.settings = load_settings(data_dir=Path(self.tmp), relevance_threshold=0.0)
        self.svc = HealthDocService(self.settings, use_llm=False)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def add(self, name, data, ctype="application/pdf"):
        doc, dup = self.svc.upload(name, ctype, data)
        return self.svc.process(doc["id"]) if not dup else doc
