from __future__ import annotations
from app.services.nlp.text import split_sentences


def chunk_page(text: str, size: int = 700, overlap: int = 120) -> list[str]:
    """Sentence-aligned chunks of about `size` characters; each chunk starts with trailing sentences of the previous
    one (up to `overlap` characters) so context is not cut mid-thought."""
    sents = split_sentences(text)
    chunks, cur = [], []
    for s in sents:
        if cur and sum(len(x) + 1 for x in cur) + len(s) > size:
            chunks.append(" ".join(cur))
            tail, n = [], 0
            for x in reversed(cur):
                if n + len(x) > overlap:
                    break
                tail.insert(0, x); n += len(x) + 1
            cur = tail
        cur.append(s)
    if cur and (not chunks or " ".join(cur) != chunks[-1]):
        chunks.append(" ".join(cur))
    return [c for c in chunks if c.strip()]


def build_chunks(doc_id: str, pages: list[dict], size: int, overlap: int) -> list[dict]:
    out = []
    for p in pages:
        for i, t in enumerate(chunk_page(p["text"], size, overlap)):
            out.append({"id": f"{doc_id}:{p['page_no']}:{i}", "doc_id": doc_id, "page_no": p["page_no"],
                        "idx": i, "text": t, "source": p["source"]})
    return out
