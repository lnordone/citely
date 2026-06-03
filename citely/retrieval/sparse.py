"""SparseRetriever — wraps the BM25 SparseIndex into RetrievedPassage results.

# TODO(phase 5): run SparseIndex.search, hydrate passages/PaperRef from the repository.
"""

from __future__ import annotations

from citely.indexing.bm25_index import SparseIndex
from citely.retrieval.types import RetrievedPassage


class SparseRetriever:
    def __init__(self, index: SparseIndex) -> None:
        self._index = index

    async def retrieve(self, query: str, top_n: int) -> list[RetrievedPassage]:
        raise NotImplementedError  # TODO(phase 5)
