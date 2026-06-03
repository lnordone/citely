"""DenseRetriever — pgvector cosine search (flat now, HNSW later).

Embeds the query via the injected EmbeddingProvider, then queries the repository and
hydrates the hits (text + parent PaperRef) for downstream reranking/rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from citely.providers.base import EmbeddingProvider
from citely.retrieval.types import PaperRef, QueryFilters, RetrievedPassage

if TYPE_CHECKING:
    from citely.db.repository import PassageRepository


class DenseRetriever:
    def __init__(self, embedder: EmbeddingProvider, repository: PassageRepository) -> None:
        self._embedder = embedder
        self._repository = repository

    async def retrieve(
        self, query: str, top_n: int, filters: QueryFilters | None = None
    ) -> list[RetrievedPassage]:
        vector = (await self._embedder.embed([query]))[0]
        scored = await self._repository.search_dense(vector, top_n, filters)
        hydrated = await self.hydrate([pid for pid, _ in scored])
        out: list[RetrievedPassage] = []
        for pid, distance in scored:
            passage = hydrated.get(pid)
            if passage is None:
                continue
            # pgvector cosine distance in [0, 2] -> similarity in [-1, 1].
            passage.score = 1.0 - distance
            out.append(passage)
        return out

    async def filter_ids(self, ids: list[str], filters: QueryFilters) -> set[str]:
        """Subset of ``ids`` whose parent paper satisfies ``filters`` (for any leg)."""
        return set(await self._repository.filter_passage_ids(ids, filters))

    async def hydrate(self, ids: list[str]) -> dict[str, RetrievedPassage]:
        """Build RetrievedPassages (with PaperRef) for the given passage ids."""
        rows = await self._repository.get_many_with_papers(ids)
        result: dict[str, RetrievedPassage] = {}
        for pid, passage in rows.items():
            paper = passage.paper
            ref = PaperRef(
                paper_id=paper.id,
                title=paper.title,
                authors=list(paper.authors),
                year=paper.published.year if paper.published else None,
                url=paper.pdf_url,
            )
            result[pid] = RetrievedPassage(
                passage_id=passage.id,
                paper_id=passage.paper_id,
                text=passage.text,
                score=0.0,
                paper=ref,
            )
        return result
