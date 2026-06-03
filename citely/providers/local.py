"""Local embedding provider via sentence-transformers (default: BAAI/bge-base-en-v1.5).

NOTE (flagged addition): the blueprint's provider file list (ollama/openai/anthropic)
has no file for the *default* embedding path (``embedding_provider: local``). This file
fills that gap. ``sentence_transformers`` (and torch) are imported lazily so importing
this module — or the rest of the tree — does not require the heavy ML stack until a
local embedder is actually built.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from citely.config import Config
from citely.providers.base import EmbeddingProvider

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model: str = "BAAI/bge-base-en-v1.5",
        batch_size: int = 64,
        normalize: bool = True,
    ) -> None:
        self._model_name = model
        self._batch_size = batch_size
        self._normalize = normalize
        self._model: SentenceTransformer | None = None

    def _ensure_model(self) -> SentenceTransformer:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        dim = self._ensure_model().get_sentence_embedding_dimension()
        if dim is None:
            raise RuntimeError(f"could not determine dimension for {self._model_name}")
        return int(dim)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_model()

        def _encode() -> list[list[float]]:
            vecs = model.encode(
                texts,
                batch_size=self._batch_size,
                normalize_embeddings=self._normalize,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return vecs.tolist()

        # Keep the event loop free during a CPU/GPU-bound encode.
        return await asyncio.to_thread(_encode)


def build_local_embedding(cfg: Config) -> LocalEmbeddingProvider:
    return LocalEmbeddingProvider(model=cfg.models.local_embed)
