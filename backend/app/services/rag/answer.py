from __future__ import annotations
import re
import time

from app.services.nlp.text import STOP, content_terms, split_sentences, stem, tokens
from app.services.rag.llm import build_prompt

ABSTAIN = "I couldn’t find enough supporting information in the selected documents to answer that confidently."

INJECTION = [re.compile(p, re.I) for p in (
    r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
    r"disregard (all |any )?(the )?(previous|prior|above|your) ",
    r"system prompt",
    r"\byou (must|should|will) (now |always )?(answer|respond|reply|tell|say|state|confirm)\b",
    r"\bnew instructions?\b",
    r"as an ai (model|assistant)",
)]
NUM = re.compile(r"\$\d[\d,]*|\d+(?:\.\d+)?\s*(?:%|days?|months?|years?|visits?)", re.I)


def is_injection(sentence: str) -> bool:
    return any(p.search(sentence) for p in INJECTION)


def _sig(s: str) -> frozenset:
    return frozenset(re.sub(r"[\s,]", "", m).lower().rstrip("s") for m in NUM.findall(s))


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def validate_citations(cites, retrieved_by_id, store) -> None:
    """Marks each citation valid only if its chunk was retrieved, document/page agree with that chunk, the excerpt is
    literally contained in the chunk, and the stored page text for that document/page contains it too."""
    for c in cites:
        ch = retrieved_by_id.get(c["chunk_id"])
        ok = bool(ch) and ch["doc_id"] == c["document_id"] and ch["page_no"] == c["page_no"] \
            and _norm(c["excerpt"]) in _norm(ch["text"])
        if ok:
            page = next((p for p in store.get_pages(c["document_id"]) if p["page_no"] == c["page_no"]), None)
            ok = bool(page) and _norm(c["excerpt"]) in _norm(page["text"])
        c["valid"] = ok


def _abstain(cov, retrieval_ms, flagged, note=None):
    return {"answer": ABSTAIN, "abstained": True, "mode": "abstain", "citations": [], "conflict": False,
            "coverage": round(cov, 3), "retrieval_ms": retrieval_ms, "generation_ms": 0, "injection_filtered": flagged,
            "evidence_type": "none", "notes": [note] if note else []}


def answer_question(index, store, settings, question, doc_ids=None, context_query=None, llm=None, threshold=None):
    q = f"{context_query} {question}" if context_query else question
    k = settings.top_k
    t0 = time.perf_counter()
    pool = index.search(q, k=max(20, k), doc_ids=doc_ids)
    retrieval_ms = round((time.perf_counter() - t0) * 1000, 2)
    flagged = False
    for h in pool:  # document text is data: drop sentences that try to instruct the assistant
        sents = split_sentences(h.chunk["text"])
        keep = [s for s in sents if not is_injection(s)]
        flagged |= len(keep) < len(sents)
        h.extra["sents"], h.extra["safe"] = keep, " ".join(keep)
    top = pool[:k]
    cov = index.coverage(q, [h.extra["safe"] for h in top], doc_ids) if top else 0.0
    thr = settings.threshold if threshold is None else threshold
    if top and settings.abstain_on_unseen_terms:
        gone = set(index.unseen_terms(q, doc_ids))
        if gone:  # a question term that appears nowhere in the selected documents cannot be answered from them
            words = list(dict.fromkeys(w for w in tokens(q) if w not in STOP and stem(w) in gone))
            return _abstain(cov, retrieval_ms, flagged, "Not mentioned in the selected documents: " + ", ".join(words))
    if not top or cov < thr:
        return _abstain(cov, retrieval_ms, flagged)

    w = index.term_weights(q, doc_ids)
    total = sum(w.values()) or 1.0

    def cands(hits):
        out = []
        for h in hits:
            for s in h.extra["sents"]:
                words = s.rstrip(".").split()
                if len(content_terms(s)) < 3 or len(words) < 5 or sum(x[0].isupper() for x in words) >= 0.8 * len(words):
                    continue  # headings, titles and fragments are not evidence
                ov = {t for t in set(content_terms(s)) if t in w}
                if ov:
                    out.append({"sent": s, "hit": h, "ov": ov, "mass": sum(w[t] for t in ov),
                                "dens": sum(w[t] for t in ov) / len(content_terms(s))})
        return out

    # conflicts: best sentence per document, only when documents were not narrowed to one
    chosen, conflict = [], False
    best: dict = {}
    for c in cands(pool):
        d = c["hit"].chunk["doc_id"]
        if d not in best or c["mass"] > best[d]["mass"]:
            best[d] = c
    strong = [c for c in best.values() if c["mass"] / total >= 0.6 and _sig(c["sent"])]
    if len(strong) >= 2:
        sigs = [_sig(c["sent"]) for c in strong]
        if not frozenset.intersection(*sigs):
            conflict, chosen = True, sorted(strong, key=lambda c: c["hit"].rank)
    if not chosen:  # greedy weighted cover over the top-k passages
        pool_c, unc = cands(top), set(w)
        while pool_c and len(chosen) < 5:
            c = max(pool_c, key=lambda c: (round(sum(w[t] for t in c["ov"] & unc), 6), c["dens"], -c["hit"].rank))
            gain = sum(w[t] for t in c["ov"] & unc)
            if gain <= 0 or (chosen and gain < 0.12 * total):
                break
            gain_set = c["ov"] & unc
            ties = [x for x in pool_c if x is not c and x["ov"] & unc == gain_set][:2]
            for x in [c, *ties]:  # equally good sentences are all shown rather than guessing between them
                chosen.append(x); pool_c.remove(x)
            unc -= c["ov"]
    if not chosen:
        return _abstain(cov, retrieval_ms, flagged)

    names: dict = {}
    cites = []
    for n, c in enumerate(chosen, 1):
        ch = c["hit"].chunk
        names.setdefault(ch["doc_id"], (store.get_document(ch["doc_id"]) or {}).get("filename", "unknown"))
        cites.append({"n": n, "document_id": ch["doc_id"], "filename": names[ch["doc_id"]], "page_no": ch["page_no"],
                      "chunk_id": ch["id"], "excerpt": c["sent"], "chunk_text": ch["text"], "source": ch["source"]})
    validate_citations(cites, {h.chunk["id"]: h.chunk for h in pool}, store)
    cites = [c for c in cites if c["valid"]]
    if not cites:
        return _abstain(cov, retrieval_ms, flagged, "Citations failed validation.")

    notes, mode, evidence_type, text, g0 = [], "extractive", "direct_source_text", None, time.perf_counter()
    if llm is not None:
        try:
            system, user = build_prompt(question, cites)
            out = llm.generate(system, user)
            cited = {int(n) for n in re.findall(r"\[(\d+)\]", out)}
            quotes = re.findall(r'"([^"]{12,})"', out)
            haystack = _norm(" ".join(c["chunk_text"] for c in cites))
            if out.strip() == ABSTAIN:
                return _abstain(cov, retrieval_ms, flagged, "The model found the evidence insufficient.")
            if not cited or not cited <= {c["n"] for c in cites}:
                notes.append("Model answer had missing or invalid citations; showing source text instead.")
            elif any(_norm(x) not in haystack for x in quotes):
                notes.append("Model answer contained a quote not found in the sources; showing source text instead.")
            else:
                text, mode, evidence_type = out.strip(), "llm", "model_summary"
                cites = [c for c in cites if c["n"] in cited]
        except Exception as e:
            notes.append(f"Language model unavailable ({type(e).__name__}); showing source text instead.")
    if text is None:
        head = "The documents give different answers:" if conflict else "From the selected documents:"
        lines = [f"• {c['excerpt']} [{c['n']}]" for c in cites]
        text = head + "\n" + "\n".join(lines)
    return {"answer": text, "abstained": False, "mode": mode, "citations": cites, "conflict": conflict,
            "coverage": round(cov, 3), "retrieval_ms": retrieval_ms,
            "generation_ms": round((time.perf_counter() - g0) * 1000, 2), "injection_filtered": flagged,
            "evidence_type": evidence_type, "notes": notes}
