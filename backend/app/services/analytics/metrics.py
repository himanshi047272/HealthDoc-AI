from __future__ import annotations
import time
from collections import Counter
from datetime import datetime


def compute_analytics(store) -> dict:
    docs = store.q("SELECT * FROM documents")
    ready = [d for d in docs if d["status"] == "ready"]
    failed = [d for d in docs if d["status"] == "failed"]
    finished = len(ready) + len(failed)
    msgs = store.q("SELECT role, abstained, created_at, latency_ms FROM messages")
    answers = [m for m in msgs if m["role"] == "assistant"]
    searches = store.q("SELECT kind, latency_ms, created_at FROM searches ORDER BY created_at DESC LIMIT 100")
    by_day = Counter(datetime.fromtimestamp(m["created_at"]).strftime("%Y-%m-%d") for m in msgs if m["role"] == "user")
    lat: dict = {}
    for s in searches:
        lat.setdefault(s["kind"], []).append(s["latency_ms"])
    cites = store.q("SELECT valid FROM citations")
    return {
        "documents_total": len(docs),
        "documents_ready": len(ready),
        "documents_failed": len(failed),
        "pages_extracted": sum(d["page_count"] or 0 for d in ready),
        "chunks_indexed": sum(d["chunk_count"] or 0 for d in ready),
        "questions_asked": sum(m["role"] == "user" for m in msgs),
        "success_rate": round(len(ready) / finished, 4) if finished else None,  # ready / (ready + failed)
        "failure_rate": round(len(failed) / finished, 4) if finished else None,
        "abstention_rate": round(sum(bool(m["abstained"]) for m in answers) / len(answers), 4) if answers else None,
        "citation_validity_rate": round(sum(bool(c["valid"]) for c in cites) / len(cites), 4) if cites else None,
        "avg_processing_ms": round(sum(d["duration_ms"] or 0 for d in ready) / len(ready)) if ready else None,
        "processing_series": [{"filename": d["filename"], "duration_ms": d["duration_ms"], "pages": d["page_count"]}
                              for d in sorted(ready, key=lambda d: d["created_at"])[-20:]],
        "search_latency_avg_ms": {k: round(sum(v) / len(v), 2) for k, v in lat.items()},
        "search_latency_series": [{"kind": s["kind"], "ms": s["latency_ms"]} for s in reversed(searches)],
        "questions_per_day": [{"day": d, "count": c} for d, c in sorted(by_day.items())][-14:],
        "recent_documents": [{"id": d["id"], "filename": d["filename"], "status": d["status"], "page_count": d["page_count"],
                              "updated_at": d["updated_at"], "is_demo": bool(d["is_demo"])}
                             for d in sorted(docs, key=lambda d: d["updated_at"], reverse=True)[:8]],
        "generated_at": time.time(),
    }
