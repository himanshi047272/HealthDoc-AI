from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"


def _env(name: str, default):
    v = os.getenv(f"HEALTHDOC_{name}")
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes") if isinstance(default, bool) else type(default)(v)


@dataclass
class Settings:
    data_dir: Path = ROOT / "data"
    max_upload_mb: int = 25
    max_pages: int = 300
    chunk_chars: int = 700
    chunk_overlap: int = 120
    top_k: int = 5
    abstain_on_unseen_terms: bool = True
    embedder: str = "tfidf"  # tfidf | sbert
    sbert_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ocr_enabled: bool = True
    min_page_chars: int = 40
    relevance_threshold: float | None = None
    llm_provider: str = "none"  # none | openai_compatible
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""
    cors_origins: str = "http://localhost:5173"

    @property
    def db_path(self) -> Path:
        return Path(self.data_dir) / "healthdoc.sqlite3"

    @property
    def upload_dir(self) -> Path:
        return Path(self.data_dir) / "uploads"

    @property
    def threshold(self) -> float:
        if self.relevance_threshold is not None:
            return self.relevance_threshold
        f = FIXTURES / "calibration.json"
        if f.exists():
            return float(json.loads(f.read_text())["relevance_threshold"])
        return 0.5


def load_settings(**overrides) -> Settings:
    s = Settings(
        data_dir=Path(os.getenv("HEALTHDOC_DATA_DIR", str(ROOT / "data"))),
        max_upload_mb=_env("MAX_UPLOAD_MB", 25),
        max_pages=_env("MAX_PAGES", 300),
        chunk_chars=_env("CHUNK_CHARS", 700),
        chunk_overlap=_env("CHUNK_OVERLAP", 120),
        top_k=_env("TOP_K", 5),
        embedder=_env("EMBEDDER", "tfidf"),
        sbert_model=_env("SBERT_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        ocr_enabled=_env("OCR_ENABLED", True),
        llm_provider=_env("LLM_PROVIDER", "none"),
        llm_base_url=_env("LLM_BASE_URL", ""),
        llm_model=_env("LLM_MODEL", ""),
        llm_api_key=os.getenv("HEALTHDOC_LLM_API_KEY", ""),
        cors_origins=_env("CORS_ORIGINS", "http://localhost:5173"),
    )
    for k, v in overrides.items():
        setattr(s, k, v)
    return s
