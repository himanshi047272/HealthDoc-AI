"""Retrieval / answer evaluation on the synthetic corpus. Runs the real ingestion pipeline in a temp directory."""
from __future__ import annotations
import json
import statistics
import tempfile
from pathlib import Path

from app.core.config import FIXTURES, load_settings
from app.services.rag.answer import answer_question


def _decision_metrics(rows, thr):
    tp = sum(r["answerable"] and r["cov"] >= thr for r in rows)
    fp = sum(not r["answerable"] and r["cov"] >= thr for r in rows)
    fn = sum(r["answerable"] and r["cov"] < thr for r in rows)
    tn = sum(not r["answerable"] and r["cov"] < thr for r in rows)
    p = tp / (tp + fp) if tp + fp else 0.0
    r_ = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r_ / (p + r_) if p + r_ else 0.0
    return {"precision": p, "recall": r_, "f1": f1, "abstention_correct": tn / (tn + fp) if tn + fp else None,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def calibrate_threshold(rows) -> float:
    """Pick the coverage threshold that maximises answer/abstain F1 (ties: accuracy, then the middle of the tied range)."""
    vals = sorted({r["cov"] for r in rows})
    cands = [0.0] + [(a + b) / 2 for a, b in zip(vals, vals[1:])] + [vals[-1] + 1e-6 if vals else 1.0]
    scored = []
    for t in cands:
        m = _decision_metrics(rows, t)
        scored.append((m["f1"], (m["tp"] + m["tn"]) / len(rows), t))
    best = max((s[0], s[1]) for s in scored)
    tied = sorted(s[2] for s in scored if (s[0], s[1]) == best)
    return round(tied[0], 4)  # lowest tied value: stay permissive, the unseen-term rule handles clear misses


def run_eval(cases_path=None, k=5, threshold=None, data_dir=None):
    from app.services.app_service import HealthDocService
    cases = json.loads(Path(cases_path or FIXTURES / "eval_cases.json").read_text())["cases"]
    
    with tempfile.TemporaryDirectory() as tmp:
        s = load_settings(data_dir=Path(data_dir or tmp))
        svc = HealthDocService(s, background=False, use_llm=False)

        try:
            docs = svc.load_demo()
            ready = [
                d for d in svc.store.q("SELECT * FROM documents")
                if d["status"] == "ready"
            ]
            name2id = {d["filename"]: d["id"] for d in ready}
            id2name = {v: k for k, v in name2id.items()}
            idx = svc.get_index()
            thr = s.threshold if threshold is None else threshold
            rows = []

            for c in cases:
                ids = [name2id[f] for f in c["filter"] if f in name2id] or None
                hits = idx.search(c["question"], k, ids)
                keys = [
                    f"{id2name[h.chunk['doc_id']]}#{h.chunk['page_no']}"
                    for h in hits
                ]
                rel = set(c["relevant"])
                ans = answer_question(
                    idx, svc.store, s, c["question"], ids, threshold=0.0
                )
                cites = ans["citations"]
                ckeys = [
                    f"{c_['filename']}#{c_['page_no']}" for c_ in cites
                ]
                evid = " ".join(c_["excerpt"] for c_ in cites).lower()

                rows.append({
                    "id": c["id"],
                    "question": c["question"],
                    "answerable": c["answerable"],
                    "tag": c.get("tag", ""),
                    "cov": ans["coverage"] if not ans["abstained"] else 0.0,
                    "recall_at_k": len(rel & set(keys)) / len(rel) if rel else None,
                    "rr": next(
                        (1 / (i + 1) for i, key in enumerate(keys) if key in rel),
                        0.0,
                    ) if rel else None,
                    "supported": (
                        all(f.lower() in evid for f in c["facts"])
                        if c["answerable"] and cites else False
                    ),
                    "n_cites": len(cites),
                    "valid_cites": sum(bool(c_["valid"]) for c_ in cites),
                    "relevant_cites": sum(k_ in rel for k_ in ckeys),
                    "pages_found": len(rel & set(ckeys)),
                    "pages_expected": len(rel),
                    "conflict": ans["conflict"],
                    "expects_conflict": c.get("expects_conflict", False),
                    "leak": any(
                        m.lower() in (ans["answer"] + evid).lower()
                        for m in c.get("must_not_contain", [])
                    ),
                    "injection_filtered": ans["injection_filtered"],
                    "answer": ans["answer"],
                    "citations": ckeys,
                })

        finally:
            svc.close()

    def mean(xs):
        xs = [x for x in xs if x is not None]
        return round(sum(xs) / len(xs), 4) if xs else None

    def metrics(rs, thr_):
        ans_rows = [r for r in rs if r["answerable"]]
        answered = [r for r in rs if r["cov"] >= thr_]
        dm = _decision_metrics(rs, thr_)
        cites = sum(r["n_cites"] for r in answered)
        return {
            "n_cases": len(rs), "n_answerable": len(ans_rows), "n_unanswerable": len(rs) - len(ans_rows),
            "retrieval_recall_at_k": mean(r["recall_at_k"] for r in ans_rows),
            "mrr": mean(r["rr"] for r in ans_rows),
            "answer_decision_precision": round(dm["precision"], 4), "answer_decision_recall": round(dm["recall"], 4),
            "answer_decision_f1": round(dm["f1"], 4),
            "correct_abstention_rate": None if dm["abstention_correct"] is None else round(dm["abstention_correct"], 4),
            "answer_support_rate": round(sum(r["supported"] and r["cov"] >= thr_ for r in ans_rows) / len(ans_rows), 4) if ans_rows else None,
            "citation_validity_rate": round(sum(r["valid_cites"] for r in answered) / cites, 4) if cites else None,
            "citation_precision": round(sum(r["relevant_cites"] for r in answered if r["answerable"]) /
                                        max(1, sum(r["n_cites"] for r in answered if r["answerable"])), 4),
            "citation_page_recall": round(sum(r["pages_found"] for r in answered if r["answerable"]) /
                                          max(1, sum(r["pages_expected"] for r in answered if r["answerable"])), 4),
            "conflict_detected_rate": mean(r["conflict"] for r in rs if r["expects_conflict"] and r["cov"] >= thr_),
            "false_conflict_rate": mean(r["conflict"] for r in answered if not r["expects_conflict"]),
            "leak_or_injection_failures": sum(r["leak"] and r["cov"] >= thr_ for r in rs),
            "confusion": {k: dm[k] for k in ("tp", "fp", "fn", "tn")},
        }
    m = metrics(rows, thr)
    m["processing_success_rate"] = round(len(ready) / len(docs), 4) if docs else None
    m["threshold"] = thr
    m["threshold_source"] = "override" if threshold is not None else "fixtures/calibration.json (fit on this same set)"
    # leave-one-out: threshold chosen without the case being scored
    loo = []
    for i, r in enumerate(rows):
        t = calibrate_threshold(rows[:i] + rows[i + 1:])
        loo.append({**r, "cov": r["cov"], "_t": t})
    tp = sum(r["answerable"] and r["cov"] >= r["_t"] for r in loo); fp = sum(not r["answerable"] and r["cov"] >= r["_t"] for r in loo)
    fn = sum(r["answerable"] and r["cov"] < r["_t"] for r in loo); tn = sum(not r["answerable"] and r["cov"] < r["_t"] for r in loo)
    m["leave_one_out"] = {"answer_decision_precision": round(tp / (tp + fp), 4) if tp + fp else None,
                          "answer_decision_recall": round(tp / (tp + fn), 4) if tp + fn else None,
                          "correct_abstention_rate": round(tn / (tn + fp), 4) if tn + fp else None}
    tags = sorted({r["tag"] for r in rows if r["tag"]})
    m["by_tag"] = {t: {"n": sum(r["tag"] == t for r in rows),
                       "support": round(sum(r["supported"] and r["cov"] >= thr for r in rows if r["tag"] == t and r["answerable"]) /
                                        max(1, sum(r["tag"] == t and r["answerable"] for r in rows)), 2)} for t in tags}
    m["without_paraphrase"] = metrics([r for r in rows if r["tag"] != "paraphrase"], thr)
    m["embedder"] = svc._proto.name
    for r in rows:
        r.pop("cov", None) if False else None
    return {"metrics": m, "results": rows}
