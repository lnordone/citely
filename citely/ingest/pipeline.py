"""Orchestrates fetch -> normalize -> chunk -> store. Idempotent (dedup on arxiv id).

Pulls raw records from :class:`ArxivClient`, normalizes each into a ``Paper``, chunks its
abstract into ``Passage`` rows, and upserts both through the repositories. Writes commit
per paper so a long harvest is resumable and a single bad record cannot roll back prior
progress.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from citely.config import Config
from citely.db.models import Passage
from citely.db.repository import PaperRepository, PassageRepository
from citely.db.session import init_db
from citely.ingest.arxiv_client import ArxivClient
from citely.ingest.chunker import Chunker
from citely.ingest.normalize import normalize_record
from citely.logging import get_logger

if TYPE_CHECKING:
    from citely.providers.base import EmbeddingProvider

log = get_logger(__name__)


@dataclass
class IngestStats:
    papers_seen: int = 0
    papers_stored: int = 0
    passages_stored: int = 0
    passages_embedded: int = 0


async def stream_ingest(
    cfg: Config,
    categories: list[str] | None = None,
    max_papers: int | None = None,
    embedder: EmbeddingProvider | None = None,
) -> AsyncIterator[dict]:
    """Fetch, normalize, chunk and store papers, yielding progress dicts for SSE.

    Yields ``{"phase": "fetch", "papers": n, "passages": n, "max_papers": N}`` after each
    paper is committed, and ``{"phase": "embed", "embedded": n, "total": N}`` after each
    embedding batch. The final event is ``{"phase": "done", ...IngestStats fields}``.

    When ``embedder`` is ``None``, the embed phase is skipped.
    """
    categories = categories or list(cfg.ingest.categories)
    max_papers = max_papers if max_papers is not None else cfg.ingest.max_papers

    client = ArxivClient(request_timeout_s=cfg.providers.request_timeout_s)
    chunker = Chunker(cfg.ingest.chunk_tokens, cfg.ingest.chunk_overlap)
    factory = init_db(cfg)

    stats = IngestStats()
    async with factory() as session:
        papers_repo = PaperRepository(session)
        passages_repo = PassageRepository(session)
        async for record in client.search(categories, max_papers):
            stats.papers_seen += 1
            try:
                paper = normalize_record(record)
            except (ValueError, KeyError) as exc:
                log.warning("ingest.skip_bad_record", error=str(exc), raw_id=record.get("id"))
                continue

            rows = [
                Passage(
                    id=chunk.id,
                    paper_id=chunk.paper_id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                )
                for chunk in chunker.chunk(paper.id, paper.abstract)
            ]
            await papers_repo.upsert(paper)
            await passages_repo.bulk_upsert(rows)
            await session.commit()

            stats.papers_stored += 1
            stats.passages_stored += len(rows)
            if stats.papers_stored % 100 == 0:
                log.info(
                    "ingest.progress",
                    papers=stats.papers_stored,
                    passages=stats.passages_stored,
                )
            yield {
                "phase": "fetch",
                "papers": stats.papers_stored,
                "passages": stats.passages_stored,
                "max_papers": max_papers,
            }

    if embedder is not None:
        from citely.indexing.embedder import build_embedder

        async for _batch, cumulative, grand_total in build_embedder(
            cfg, embedder, batch_size=64
        ).index_all_streaming():
            stats.passages_embedded = cumulative
            yield {"phase": "embed", "embedded": cumulative, "total": grand_total}

    async with factory() as session:
        total_embedded = await PassageRepository(session).count_embedded()

    log.info(
        "ingest.done",
        papers_seen=stats.papers_seen,
        papers_stored=stats.papers_stored,
        passages_stored=stats.passages_stored,
        passages_embedded=stats.passages_embedded,
        total_embedded=total_embedded,
    )
    yield {
        "phase": "done",
        "papers_stored": stats.papers_stored,
        "passages_stored": stats.passages_stored,
        "passages_embedded": stats.passages_embedded,
        "total_embedded": total_embedded,
    }


async def run_ingest(
    cfg: Config,
    categories: list[str] | None = None,
    max_papers: int | None = None,
    embedder: EmbeddingProvider | None = None,
) -> IngestStats:
    """Non-streaming wrapper around :func:`stream_ingest` for CLI / test use."""
    stats = IngestStats()
    async for event in stream_ingest(cfg, categories, max_papers, embedder):
        if event["phase"] == "done":
            stats.papers_stored = event["papers_stored"]
            stats.passages_stored = event["passages_stored"]
            stats.passages_embedded = event["passages_embedded"]
    return stats
