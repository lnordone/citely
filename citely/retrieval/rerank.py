"""Cross-encoder reranker. Scores (query, passage) PAIRS — a distinct interface.

Default: BAAI/bge-reranker-base via sentence-transformers. The model is loaded lazily so
constructing the reranker (e.g. in the provider factory) is cheap and import-safe.

# TODO(phase 5): load CrossEncoder lazily, score pairs, return top_k re-sorted.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from citely.retrieval.types import RetrievedPassage


class Reranker(ABC):
    @abstractmethod
    async def rerank(
        self, query: str, passages: list[RetrievedPassage], top_k: int
    ) -> list[RetrievedPassage]:
        """Score (query, passage) pairs with a cross-encoder; return top_k re-sorted."""


class CrossEncoderReranker(Reranker):
    def __init__(self, model: str = "BAAI/bge-reranker-base", final_k: int = 8) -> None:
        self._model_name = model
        self._final_k = final_k
        self._model = None  # sentence_transformers.CrossEncoder, loaded lazily

    async def rerank(
        self, query: str, passages: list[RetrievedPassage], top_k: int
    ) -> list[RetrievedPassage]:
        raise NotImplementedError  # TODO(phase 5)
