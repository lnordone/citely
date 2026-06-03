"""Cross-encoder reranker. Scores (query, passage) PAIRS — a distinct interface.

Default: BAAI/bge-reranker-base via sentence-transformers. The model is loaded lazily so
constructing the reranker (e.g. in the provider factory) is cheap and import-safe.

# TODO(phase 5): load CrossEncoder lazily, score pairs, return top_k re-sorted.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from citely.retrieval.types import RetrievedPassage

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder


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
        self._model: CrossEncoder | None = None

    def _ensure_model(self) -> CrossEncoder:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)
        return self._model

    async def rerank(
        self, query: str, passages: list[RetrievedPassage], top_k: int
    ) -> list[RetrievedPassage]:
        if not passages:
            return []
        model = self._ensure_model()
        pairs = [(query, p.text) for p in passages]

        def _predict() -> list[float]:
            # CrossEncoder.predict's typed signature is an over-broad union; a list of
            # (query, passage) string pairs is the documented input.
            raw = model.predict(pairs, show_progress_bar=False)  # type: ignore[arg-type]
            return [float(s) for s in raw]

        # Cross-encoder inference is CPU/GPU-bound; keep the event loop free.
        scores = await asyncio.to_thread(_predict)
        for passage, score in zip(passages, scores, strict=True):
            passage.score = score
        passages.sort(key=lambda p: p.score, reverse=True)
        return passages[:top_k]
