"""In-process BM25 sparse index over passages (MVP: rank_bm25).

Behind the ``SparseIndex`` interface so OpenSearch can replace rank_bm25 later without
touching retrieval.

"""

from __future__ import annotations

import pickle
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from rank_bm25 import BM25Okapi

if TYPE_CHECKING:
    from citely.db.models import Passage

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenization (alphanumeric runs)."""
    return _TOKEN_RE.findall(text.lower())


class SparseIndex(ABC):
    @abstractmethod
    def build(self, passages: list[Passage]) -> None: ...

    @abstractmethod
    def search(self, query: str, top_n: int) -> list[tuple[str, float]]:
        """Returns [(passage_id, score)] ranked."""

    @abstractmethod
    def save(self, path: str) -> None: ...

    @abstractmethod
    def load(self, path: str) -> None: ...


class BM25Index(SparseIndex):
    def __init__(self) -> None:
        self._ids: list[str] = []
        self._model: BM25Okapi | None = None

    def build(self, passages: list[Passage]) -> None:
        self._ids = [p.id for p in passages]
        corpus = [_tokenize(p.text) for p in passages]
        # BM25Okapi requires a non-empty corpus; guard the empty case.
        self._model = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_n: int) -> list[tuple[str, float]]:
        if self._model is None or not self._ids:
            return []
        scores = self._model.get_scores(_tokenize(query))
        ranked = sorted(zip(self._ids, scores, strict=True), key=lambda x: x[1], reverse=True)
        return [(pid, float(score)) for pid, score in ranked[:top_n]]

    def save(self, path: str) -> None:
        with open(path, "wb") as fh:
            pickle.dump({"ids": self._ids, "model": self._model}, fh)

    def load(self, path: str) -> None:
        with open(path, "rb") as fh:
            state = pickle.load(fh)
        self._ids = state["ids"]
        self._model = state["model"]
