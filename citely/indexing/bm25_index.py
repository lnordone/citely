"""In-process BM25 sparse index over passages (MVP: rank_bm25).

Behind the ``SparseIndex`` interface so OpenSearch can replace rank_bm25 later without
touching retrieval.

# TODO(phase 4): tokenize passages, build BM25Okapi, implement search/save/load.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citely.db.models import Passage


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
        self._model = None  # rank_bm25.BM25Okapi, built in build()

    def build(self, passages: list[Passage]) -> None:
        raise NotImplementedError  # TODO(phase 4)

    def search(self, query: str, top_n: int) -> list[tuple[str, float]]:
        raise NotImplementedError  # TODO(phase 4)

    def save(self, path: str) -> None:
        raise NotImplementedError  # TODO(phase 4)

    def load(self, path: str) -> None:
        raise NotImplementedError  # TODO(phase 4)
