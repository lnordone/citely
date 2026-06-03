"""Batch passages through the EmbeddingProvider and write vectors back to the DB.

Receives the EmbeddingProvider via DI — never instantiates a client directly.

# TODO(phase 4): stream passages, embed in batches, persist embedding (+ int8 toggle).
"""

from __future__ import annotations

from citely.providers.base import EmbeddingProvider


class Embedder:
    def __init__(self, embedder: EmbeddingProvider, batch_size: int = 128) -> None:
        self._embedder = embedder
        self._batch_size = batch_size

    async def index_all(self) -> int:
        """Embed all un-embedded passages; return the count written."""
        raise NotImplementedError  # TODO(phase 4)
