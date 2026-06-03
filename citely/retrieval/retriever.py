"""HybridRetriever — orchestrates the whole retrieval pipeline.

construct -> {sparse, dense legs} -> RRF fusion -> rerank -> assign source keys -> final_k.
All sub-components (retrievers, reranker) are injected; providers reach it only via those.

# TODO(phase 5): orchestrate the legs, fuse, rerank, apply filters per filter_order,
# assign S1.. source keys.
"""

from __future__ import annotations

from citely.config import Config
from citely.retrieval.dense import DenseRetriever
from citely.retrieval.rerank import Reranker
from citely.retrieval.sparse import SparseRetriever
from citely.retrieval.types import RetrievalResult


class HybridRetriever:
    def __init__(
        self,
        cfg: Config,
        sparse: SparseRetriever,
        dense: DenseRetriever,
        reranker: Reranker,
    ) -> None:
        self._cfg = cfg
        self._sparse = sparse
        self._dense = dense
        self._reranker = reranker

    async def retrieve(self, query: str) -> RetrievalResult:
        raise NotImplementedError  # TODO(phase 5)
