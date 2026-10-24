from __future__ import annotations
import logging

from app.services.nlp.text import STOP, tokens

log = logging.getLogger("healthdoc.embed")


class EmbedderUnavailable(Exception):
    pass


class TfidfEmbedder:
    """Offline fallback. Character n-gram TF-IDF vectors: they tolerate word-form differences ('exclusion' vs
    'excluded') but are NOT semantic embeddings and will not match true synonyms."""
    name = "tfidf-char-ngram (offline fallback, lexical)"
    semantic = False

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.v = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)

    @staticmethod
    def _prep(t: str) -> str:
        return " ".join(w for w in tokens(t) if w not in STOP)

    def fit(self, texts):
        self.v.fit([self._prep(t) for t in texts])

    def encode(self, texts):
        return self.v.transform([self._prep(t) for t in texts])


class SbertEmbedder:
    """Pretrained sentence-transformers model, loaded lazily and cached on the instance."""
    semantic = True

    def __init__(self, model_name: str):
        self.name = model_name
        try:
            from sentence_transformers import SentenceTransformer
            self.m = SentenceTransformer(model_name)
        except Exception as e:  # import error, offline, download failure, out of memory
            raise EmbedderUnavailable(f"{type(e).__name__}: could not load '{model_name}'") from e
        self._cache: dict[str, object] = {}

    def fit(self, texts):
        pass

    def encode(self, texts):
        import numpy as np
        missing = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if missing:
            for t, v in zip(missing, self.m.encode(missing, normalize_embeddings=True, show_progress_bar=False)):
                self._cache[t] = v
        return np.vstack([self._cache[t] for t in texts])


def get_embedder(settings):
    """Returns (embedder, note). Falls back to TF-IDF and says why."""
    if settings.embedder == "sbert":
        try:
            return SbertEmbedder(settings.sbert_model), None
        except EmbedderUnavailable as e:
            log.warning("falling back to tfidf: %s", e)
            return TfidfEmbedder(), f"{e}. Using the offline lexical fallback."
    return TfidfEmbedder(), None
