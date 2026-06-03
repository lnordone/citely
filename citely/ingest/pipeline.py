"""Orchestrates fetch -> normalize -> chunk -> store. Idempotent (dedup on arxiv id).

# TODO(phase 3): wire ArxivClient -> normalize_record -> Chunker -> repositories.
"""

from __future__ import annotations

from dataclasses import dataclass

from citely.config import Config


@dataclass
class IngestStats:
    papers_seen: int = 0
    papers_stored: int = 0
    passages_stored: int = 0


async def run_ingest(
    cfg: Config,
    categories: list[str] | None = None,
    max_papers: int | None = None,
) -> IngestStats:
    """Fetch, normalize, chunk and store papers. Safe to re-run (idempotent)."""
    raise NotImplementedError  # TODO(phase 3)
