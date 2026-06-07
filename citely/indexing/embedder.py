"""Batch passages through the EmbeddingProvider and write vectors back to the DB.

Receives the EmbeddingProvider via DI — never instantiates a client directly. Streams
un-embedded passages in batches (bounded memory, resumable: each committed batch is
skipped on a re-run), optionally also writing the int8-quantized representation.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from citely.config import Config
from citely.db.repository import PassageRepository
from citely.db.session import check_embedding_dimension, get_session_factory
from citely.indexing.quantize import quantize_int8
from citely.logging import get_logger
from citely.providers.base import EmbeddingProvider

log = get_logger(__name__)


class Embedder:
    def __init__(
        self, embedder: EmbeddingProvider, batch_size: int = 128, quantize: bool = False
    ) -> None:
        self._embedder = embedder
        self._batch_size = batch_size
        self._quantize = quantize

    async def index_all(self) -> int:
        """Embed all un-embedded passages; return the count written."""
        total = 0
        async for _batch, cumulative, _grand in self.index_all_streaming():
            total = cumulative
        return total

    async def index_all_streaming(self) -> AsyncIterator[tuple[int, int, int]]:
        """Embed all un-embedded passages, yielding (batch_written, cumulative, grand_total).

        ``grand_total`` is the count of un-embedded passages measured before the first
        batch, giving callers a stable denominator for progress display.
        """
        check_embedding_dimension(self._embedder)
        factory = get_session_factory()

        async with factory() as session:
            grand_total = await PassageRepository(session).count_unembedded()

        total = 0
        while True:
            async with factory() as session:
                repo = PassageRepository(session)
                batch = await repo.fetch_unembedded(self._batch_size)
                if not batch:
                    break

                vectors = await self._embedder.embed([p.text for p in batch])
                updates: list[tuple[str, list[float], bytes | None]] = [
                    (p.id, vec, quantize_int8(vec) if self._quantize else None)
                    for p, vec in zip(batch, vectors, strict=True)
                ]
                await repo.set_embeddings(updates)
                await session.commit()

            total += len(batch)
            log.info("embed.batch", written=len(batch), total=total)
            yield len(batch), total, grand_total

        log.info("embed.done", total=total)


def build_embedder(
    cfg: Config, embedder: EmbeddingProvider, batch_size: int = 128
) -> Embedder:
    """Construct an Embedder, enabling int8 persistence per config.indexing.quantization."""
    from citely.config import QuantizationKind

    return Embedder(
        embedder,
        batch_size=batch_size,
        quantize=cfg.indexing.quantization is QuantizationKind.int8,
    )
