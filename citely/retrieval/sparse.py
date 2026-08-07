"""SparseRetriever — wraps the BM25 SparseIndex into RetrievedPassage results.

"""

from __future__ import annotations

from citely.indexing.bm25_index import SparseIndex
from citely.retrieval.types import RetrievedPassage


class SparseRetriever:
    def __init__(self, index: SparseIndex) -> None:
        self._index = index

    async def retrieve(self, query: str, top_n: int) -> list[RetrievedPassage]:
        # BM25 returns (passage_id, score); text/paper are hydrated downstream (the
        # HybridRetriever fills them once for the fused candidate set).
        return [
            RetrievedPassage(passage_id=pid, paper_id="", text="", score=score)
            for pid, score in self._index.search(query, top_n)
        ]
