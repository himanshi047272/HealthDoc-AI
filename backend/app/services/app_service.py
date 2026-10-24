"""Application facade. The API layer and the tests both go through this class."""
from __future__ import annotations
import hashlib
import re
import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from app.core.config import FIXTURES, Settings, load_settings
from app.db.store import Store
from app.services.analytics.metrics import compute_analytics
from app.services.embeddings.embedder import SbertEmbedder, TfidfEmbedder, get_embedder
from app.services.ingestion.pipeline import run_pipeline
from app.services.ingestion.validate import ALLOWED, validate_upload
from app.services.nlp.text import content_terms, extract_definitions, extract_entities, extract_fields, split_sentences
from app.services.ocr.ocr import ocr_available
from app.services.rag.answer import ABSTAIN, answer_question
from app.services.rag.llm import build_llm
from app.services.retrieval.index import HybridIndex

FOLLOW = re.compile(r"^(and|also|what about|how about|why|but)\b|\b(it|its|they|them|their|those)\b", re.I)


class NotFound(Exception):
    pass


class HealthDocService:
    def __init__(self, settings: Settings | None = None, store: Store | None = None, background: bool = False,
                 use_llm: bool = True, llm=None, embedder=None):
        self.settings = settings or load_settings()
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        self.store = store or Store(self.settings.db_path)
        self.llm = llm if llm is not None else (build_llm(self.settings) if use_llm else None)
        self._proto, self.embedder_note = (embedder, None) if embedder else get_embedder(self.settings)
        self._index, self._index_version = None, -1
        self.pool = ThreadPoolExecutor(2) if background else None
        self.recover_interrupted()

    # ---- index -------------------------------------------------------------------------------------------------
    def _new_embedder(self):
        return TfidfEmbedder() if isinstance(self._proto, TfidfEmbedder) else self._proto

    def get_index(self) -> HybridIndex:
        v = self.store.version
        if self._index is None or self._index_version != v:
            self._index = HybridIndex(self.store.get_chunks(), self._new_embedder())
            self._index_version = v
        return self._index

    def _verify_embeddings(self, doc_id):
        texts = [c["text"] for c in self.store.q("SELECT text FROM chunks WHERE doc_id=?", (doc_id,))]
        emb = self._new_embedder()
        emb.fit(texts)
        if emb.encode(texts).shape[0] != len(texts):
            raise RuntimeError("embedding count mismatch")

    # ---- documents ---------------------------------------------------------------------------------------------
    def recover_interrupted(self):
        for d in self.store.q("SELECT id FROM documents WHERE status IN ('processing','uploaded')"):
            self.store.update_document(d["id"], status="failed", error="Processing was interrupted. Use Reprocess to retry.")

    def upload(self, filename, content_type, data: bytes, is_demo=False):
        name, kind = validate_upload(filename, content_type, data, self.settings.max_upload_mb * 1024 * 1024)
        sha = hashlib.sha256(data).hexdigest()
        dup = self.store.find_by_hash(sha)
        if dup:
            return dup, True
        ext = next(e for e, k in ALLOWED.items() if k == kind)
        stored = f"{uuid.uuid4().hex}{ext}"
        (self.settings.upload_dir / stored).write_bytes(data)
        doc = self.store.add_document(filename=name, stored_name=stored, mime=content_type or kind, kind=kind,
                                      size_bytes=len(data), sha256=sha, is_demo=int(is_demo))
        return doc, False

    def process(self, doc_id):
        hook = lambda: self._verify_embeddings(doc_id)
        run = lambda: run_pipeline(self.store, self.settings, doc_id, hook)
        if self.pool:
            self.store.update_document(doc_id, status="processing", error=None)
            self.pool.submit(run)
        else:
            run()
        return self.store.get_document(doc_id)

    def get_document(self, doc_id):
        d = self.store.get_document(doc_id)
        if not d:
            raise NotFound("Document not found.")
        d["job"] = self.store.latest_job(doc_id)
        return d

    def delete_document(self, doc_id):
        d = self.get_document(doc_id)
        (self.settings.upload_dir / d["stored_name"]).unlink(missing_ok=True)
        self.store.delete_document(doc_id)

    def reprocess(self, doc_id):
        d = self.get_document(doc_id)
        if d["status"] == "processing":
            return d
        self.store.replace_chunks(doc_id, [])
        self.store.update_document(doc_id, status="uploaded", error=None)
        return self.process(doc_id)

    def pages(self, doc_id):
        self.get_document(doc_id)
        return self.store.get_pages(doc_id)

    def insights(self, doc_id):
        d = self.get_document(doc_id)
        pages = self.store.get_pages(doc_id)
        sents = [(s, p["page_no"]) for p in pages for s in split_sentences(p["text"])]
        ents, seen = [], set()
        for p in pages:
            for e in extract_entities(p["text"]):
                if (e["label"], e["text"].lower(), p["page_no"]) not in seen:
                    seen.add((e["label"], e["text"].lower(), p["page_no"]))
                    ents.append({**e, "page_no": p["page_no"]})
        defs = [{**x, "page_no": p["page_no"]} for p in pages for x in extract_definitions(p["text"])]
        return {"document_id": doc_id, "filename": d["filename"],
                "classification": {"label": d["doc_type"], "score": d["doc_type_score"], "kind": "inferred",
                                   "method": "keyword-density baseline; score is the top class's share of keyword hits, not a probability"},
                "fields": extract_fields(sents), "entities": ents, "definitions": defs,
                "ocr_pages": [p["page_no"] for p in pages if p["source"] == "ocr"]}

    # ---- search ------------------------------------------------------------------------------------------------
    def _allowed_ids(self, doc_ids=None, doc_type=None, date_from=None, date_to=None):
        ids = []
        for d in self.store.q("SELECT id, doc_type, created_at FROM documents WHERE status='ready'"):
            if doc_ids and d["id"] not in doc_ids:
                continue
            if doc_type and d["doc_type"] != doc_type:
                continue
            if date_from and d["created_at"] < date_from.timestamp():
                continue
            if date_to and d["created_at"] > date_to.timestamp():
                continue
            ids.append(d["id"])
        return ids

    def search(self, query, mode="hybrid", doc_ids=None, doc_type=None, date_from: datetime | None = None,
               date_to: datetime | None = None, k=10):
        allowed = self._allowed_ids(doc_ids, doc_type, date_from, date_to)
        t0 = time.perf_counter()
        hits = self.get_index().search(query, k=k, doc_ids=allowed, mode=mode) if allowed else []
        ms = round((time.perf_counter() - t0) * 1000, 2)
        self.store.log_search(mode, ms, len(hits))
        names = {d["id"]: d["filename"] for d in self.store.q("SELECT id, filename FROM documents")}
        return {"latency_ms": ms, "mode": mode, "total": len(hits), "results": [
            {"document_id": h.chunk["doc_id"], "filename": names.get(h.chunk["doc_id"]), "page_no": h.chunk["page_no"],
             "chunk_id": h.chunk["id"], "passage": h.chunk["text"], "source": h.chunk["source"],
             "score": round(h.score, 4), "bm25": round(h.bm25, 4), "dense": round(h.dense, 4)} for h in hits]}

    # ---- chat --------------------------------------------------------------------------------------------------
    def ask(self, question, conversation_id=None, doc_ids=None):
        if conversation_id and not self.store.conversation_exists(conversation_id):
            raise NotFound("Conversation not found.")
        conv = conversation_id or self.store.add_conversation()
        prev = [m for m in self.store.get_messages(conv) if m["role"] == "user"]
        ctx = prev[-1]["content"] if prev and (len(set(content_terms(question))) <= 2 or FOLLOW.search(question)) else None
        allowed = self._allowed_ids(doc_ids or None)
        self.store.add_message(conv, "user", question, doc_ids=doc_ids)
        t0 = time.perf_counter()
        res = answer_question(self.get_index(), self.store, self.settings, question, allowed, ctx, self.llm) if allowed else \
            {"answer": ABSTAIN, "abstained": True, "mode": "abstain", "citations": [], "conflict": False, "coverage": 0.0,
             "retrieval_ms": 0, "generation_ms": 0, "injection_filtered": False, "evidence_type": "none",
             "notes": ["No processed documents match the selection."]}
        ms = round((time.perf_counter() - t0) * 1000, 2)
        mid = self.store.add_message(conv, "assistant", res["answer"], res["mode"], res["abstained"], ms, doc_ids)
        self.store.add_citations(mid, res["citations"])
        self.store.log_search("chat", res["retrieval_ms"], len(res["citations"]))
        return {**res, "conversation_id": conv, "message_id": mid, "latency_ms": ms,
                "used_context_from_previous_question": bool(ctx)}

    def conversation(self, cid):
        if not self.store.conversation_exists(cid):
            raise NotFound("Conversation not found.")
        return {"id": cid, "messages": self.store.get_messages(cid)}

    # ---- misc --------------------------------------------------------------------------------------------------
    def analytics(self):
        return compute_analytics(self.store)

    def load_demo(self):
        out = []
        for f in sorted((FIXTURES / "docs").glob("*.pdf")):
            doc, dup = self.upload(f.name, "application/pdf", f.read_bytes(), is_demo=True)
            if not dup:
                doc = self.process(doc["id"])
            out.append({**doc, "duplicate": dup})
        return out

    def close(self):
        if self.pool is not None:
            self.pool.shutdown(wait=True)
            self.pool = None
        self.store.close()

    def run_eval(self):
        from app.services.evaluation.runner import run_eval
        r = run_eval()
        r["run_id"] = self.store.add_eval_run(r["metrics"], r["results"])
        return r

    def system_status(self):
        import importlib.util as iu
        has = lambda m: iu.find_spec(m) is not None
        try:
            self.store.q("SELECT 1"); db = True
        except Exception:
            db = False
        spacy_ok = False
        if has("spacy"):
            try:
                import spacy; spacy.load("en_core_web_sm"); spacy_ok = True
            except Exception:
                pass
        s = self.settings
        comps = {
            "database": {"ok": db, "detail": "SQLite", "fix": None},
            "ocr": {"ok": ocr_available(), "detail": "Tesseract + OpenCV preprocessing" if has("cv2") else "Tesseract (OpenCV missing)",
                    "fix": None if ocr_available() else "Install Tesseract: apt install tesseract-ocr (Linux) or brew install tesseract (macOS), then pip install pytesseract."},
            "pdf_parser": {"ok": True, "detail": "PyMuPDF" if has("fitz") else "pypdf (fallback)",
                           "fix": None if has("fitz") else "pip install PyMuPDF for faster, more accurate PDF text extraction."},
            "embeddings": {"ok": True, "detail": getattr(self._proto, "name", "custom"),
                           "semantic": bool(getattr(self._proto, "semantic", False)),
                           "fix": self.embedder_note or (None if getattr(self._proto, "semantic", False) else
                                  "Running the lexical fallback. For semantic retrieval: pip install sentence-transformers, set HEALTHDOC_EMBEDDER=sbert, and allow one model download.")},
            "spacy": {"ok": spacy_ok, "detail": "en_core_web_sm" if spacy_ok else "not loaded (regex entity extraction in use)",
                      "fix": None if spacy_ok else "pip install spacy && python -m spacy download en_core_web_sm"},
            "llm": {"ok": self.llm is not None, "detail": getattr(self.llm, "name", "not configured (extractive answers)"),
                    "fix": None if self.llm else "Optional. Set HEALTHDOC_LLM_PROVIDER, HEALTHDOC_LLM_BASE_URL, HEALTHDOC_LLM_MODEL and HEALTHDOC_LLM_API_KEY on the server."},
        }
        return {"components": comps, "external_processing": self.llm is not None,
                "privacy_note": "Documents are processed locally." if not self.llm else
                "A language model provider is configured: retrieved passages are sent to it when you ask a question.",
                "limits": {"max_upload_mb": s.max_upload_mb, "max_pages": s.max_pages, "chunk_chars": s.chunk_chars,
                           "chunk_overlap": s.chunk_overlap, "top_k": s.top_k, "relevance_threshold": s.threshold},
                "supported_types": sorted(ALLOWED)}
