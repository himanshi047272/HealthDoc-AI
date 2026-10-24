from __future__ import annotations
import logging
import time

from app.services.ingestion.chunking import build_chunks
from app.services.ingestion.extract import ProcessingError, extract_image, extract_pdf
from app.services.nlp.text import classify, normalize, strip_repeated_lines

log = logging.getLogger("healthdoc.pipeline")


def run_pipeline(store, settings, doc_id: str, index_hook=None) -> None:
    """Extract -> clean -> chunk -> index. A document becomes 'ready' only if every step succeeds."""
    doc = store.get_document(doc_id)
    if not doc:
        return
    job, t0 = store.create_job(doc_id), time.perf_counter()
    path = str(settings.upload_dir / doc["stored_name"])
    try:
        store.update_document(doc_id, status="processing", error=None)
        store.update_job(job, stage="extract")
        pages, extractor = (extract_pdf if doc["kind"] == "pdf" else extract_image)(path, settings)
        if not any(p.text.strip() for p in pages):
            raise ProcessingError("No readable text was found. The file may be blank, or OCR could not read it.")
        store.update_job(job, stage="clean")
        cleaned = strip_repeated_lines([p.text for p in pages])
        page_rows = [{"page_no": p.page_no, "text": normalize(c), "source": p.source, "ocr_conf": p.ocr_conf}
                     for p, c in zip(pages, cleaned)]
        store.replace_pages(doc_id, page_rows)
        store.update_job(job, stage="chunk")
        chunks = build_chunks(doc_id, [p for p in page_rows if p["text"]], settings.chunk_chars, settings.chunk_overlap)
        if not chunks:
            raise ProcessingError("The document produced no text chunks after cleaning.")
        store.replace_chunks(doc_id, chunks)
        store.update_job(job, stage="index")
        label, score = classify(" ".join(p["text"] for p in page_rows))
        store.update_document(doc_id, page_count=len(pages), chunk_count=len(chunks), extractor=extractor,
                              ocr_pages=sum(p.source == "ocr" for p in pages), doc_type=label, doc_type_score=score)
        if index_hook:
            index_hook()  # embeddings/index must build before we call the document ready
        ms = int((time.perf_counter() - t0) * 1000)
        store.update_document(doc_id, status="ready", duration_ms=ms)
        store.version += 1  # ready documents now join the searchable corpus
        store.update_job(job, status="done", stage="done", finished_at=time.time())
    except Exception as e:
        msg = str(e) if isinstance(e, ProcessingError) else "Unexpected processing error. Check the server log."
        log.error("processing failed doc=%s type=%s", doc_id, type(e).__name__)
        store.replace_chunks(doc_id, [])
        store.update_document(doc_id, status="failed", error=msg, duration_ms=int((time.perf_counter() - t0) * 1000))
        store.update_job(job, status="failed", error=msg, finished_at=time.time())
