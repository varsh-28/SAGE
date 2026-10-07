"""Vector index with an automatic backend choice.

backend=auto: sentence-transformers (all-MiniLM-L6-v2) if installed and the model can be loaded,
otherwise TF-IDF (scikit-learn). The chosen backend is recorded in the eval report.
Override with env var OPSGRAPH_BACKEND=tfidf|st.
"""
from __future__ import annotations

import os

import numpy as np


class VectorIndex:
    def __init__(self, backend: str | None = None):
        self.pref = backend or os.environ.get("OPSGRAPH_BACKEND", "auto")
        self.backend: str | None = None
        self.ids: list[str] = []

    def fit(self, ids: list[str], docs: list[str]) -> "VectorIndex":
        self.ids = list(ids)
        if self.pref in ("auto", "st"):
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                self._emb = self._model.encode(docs, normalize_embeddings=True, show_progress_bar=False)
                self.backend = "sentence-transformers"
                return self
            except Exception:
                if self.pref == "st":
                    raise
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b[\w-]+\b")
        self._emb = self._vec.fit_transform(docs)
        self.backend = "tfidf"
        return self

    def search(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        if self.backend == "sentence-transformers":
            qv = self._model.encode([query], normalize_embeddings=True)[0]
            sims = np.asarray(self._emb @ qv)
        else:
            sims = (self._emb @ self._vec.transform([query]).T).toarray().ravel()
        top = np.argsort(-sims)[:k]
        return [(self.ids[i], float(sims[i])) for i in top]
