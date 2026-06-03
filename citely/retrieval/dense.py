"""DenseRetriever — pgvector cosine search (flat now, HNSW later).

Embeds the query via the injected EmbeddingProvider, then queries the repository.

# TODO(phase 5): embed query, call PassageRepository.search_dense, hydrate results.
"""

from __future__ import annotations

from citely.providers.base import EmbeddingProvider
from citely.retrieval.types import QueryFilters, RetrievedPassage


class DenseRetriever:
    def __init__(self, embedder: EmbeddingProvider, repository: object) -> None:
        self._embedder = embedder
        self._repository = repository

    async def retrieve(
        self, query: str, top_n: int, filters: QueryFilters | None = None
    ) -> list[RetrievedPassage]:
        raise NotImplementedError  # TODO(phase 5)
