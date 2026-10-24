"""Hybrid retrieval: BM25 + dense cosine, max-normalised and averaged, deduplicated, filterable by document.

Ranking: score = w * bm25/max(bm25) + (1-w) * cosine/max(cosine) over the candidate set (w = 0.5).
Coverage (used for abstention) is the IDF-weighted share of the question's content terms found in the retrieved text.
Statistics are computed over the filtered subset, so a document filter never lets another document's vocabulary in."""
from __future__ import annotations
import math
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from app.services.nlp.text import content_terms


@dataclass
class Hit:
    chunk: dict
    score: float
    bm25: float = 0.0
    dense: float = 0.0
    rank: int = 0
    extra: dict = field(default_factory=dict)


class HybridIndex:
    def __init__(self, chunks, embedder, w_bm25: float = 0.5, k1: float = 1.5, b: float = 0.75):
        self.chunks, self.emb, self.w, self.k1, self.b = chunks, embedder, w_bm25, k1, b
        self.terms = [content_terms(c["text"]) for c in chunks]
        self.tf = [Counter(t) for t in self.terms]
        self.M = None
        if chunks:
            texts = [c["text"] for c in chunks]
            embedder.fit(texts)
            self.M = embedder.encode(texts)
        self._stats: dict = {}

    def _subset(self, doc_ids):
        if doc_ids is None:
            return list(range(len(self.chunks)))
        allowed = set(doc_ids)
        return [i for i, c in enumerate(self.chunks) if c["doc_id"] in allowed]

    def _stat(self, idxs):
        key = tuple(idxs)
        if key not in self._stats:
            df = Counter()
            for i in idxs:
                df.update(self.tf[i].keys())
            lens = [len(self.terms[i]) for i in idxs]
            self._stats[key] = (len(idxs), df, (sum(lens) / len(lens)) if lens else 1.0)
        return self._stats[key]

    @staticmethod
    def _idf(n, df, t):
        d = df.get(t, 0)
        return math.log(1 + (n - d + 0.5) / (d + 0.5))

    def term_weights(self, query, doc_ids=None) -> dict:
        n, df, _ = self._stat(self._subset(doc_ids))
        return {t: self._idf(n, df, t) for t in set(content_terms(query))}

    def unseen_terms(self, query, doc_ids=None) -> list:
        n, df, _ = self._stat(self._subset(doc_ids))
        return [t for t in set(content_terms(query)) if df.get(t, 0) == 0]

    def coverage(self, query, texts, doc_ids=None) -> float:
        w = self.term_weights(query, doc_ids)
        if not w:
            return 0.0
        present = set()
        for t in texts:
            present.update(content_terms(t))
        return sum(v for k, v in w.items() if k in present) / sum(w.values())

    def _dense(self, query, idxs):
        q = self.emb.encode([query])
        sub = self.M[idxs]
        r = sub @ q.T
        return np.asarray(r.toarray() if hasattr(r, "toarray") else r).ravel()

    def search(self, query, k=5, doc_ids=None, mode="hybrid") -> list[Hit]:
        idxs = self._subset(doc_ids)
        qt = list(set(content_terms(query)))
        if not idxs or not qt:
            return []
        n, df, avgdl = self._stat(idxs)
        bm = np.zeros(len(idxs))
        for j, i in enumerate(idxs):
            dl = len(self.terms[i]) or 1
            for t in qt:
                f = self.tf[i].get(t, 0)
                if f:
                    bm[j] += self._idf(n, df, t) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / avgdl))
        de = np.clip(self._dense(query, idxs), 0, None)
        nb = bm / bm.max() if bm.max() > 0 else bm
        nd = de / de.max() if de.max() > 0 else de
        score = nb if mode == "keyword" else nd if mode == "semantic" else self.w * nb + (1 - self.w) * nd
        order = np.argsort(-score, kind="stable")
        hits, kept = [], []
        for j in order:
            if score[j] <= 0:
                break
            c = self.chunks[idxs[j]]
            ts = set(self.terms[idxs[j]])
            if any(c["doc_id"] == o["doc_id"] and c["page_no"] == o["page_no"] and
                   len(ts & ots) / max(1, len(ts | ots)) > 0.6 for o, ots in kept):
                continue  # overlapping duplicate of a passage already returned
            kept.append((c, ts))
            hits.append(Hit(c, float(score[j]), float(bm[j]), float(de[j]), len(hits) + 1))
            if len(hits) >= k:
                break
        return hits
