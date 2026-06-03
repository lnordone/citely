"""HybridRetriever — orchestrates the whole retrieval pipeline.

construct -> {sparse, dense legs} -> RRF fusion -> rerank -> assign source keys -> final_k.
All sub-components (retrievers, reranker) are injected; providers reach it only via those.

# TODO(phase 5): orchestrate the legs, fuse, rerank, apply filters per filter_order,
# assign S1.. source keys.
"""

from __future__ import annotations

import asyncio

from citely.config import Config
from citely.logging import get_logger
from citely.retrieval.dense import DenseRetriever
from citely.retrieval.fusion import reciprocal_rank_fusion
from citely.retrieval.rerank import Reranker
from citely.retrieval.sparse import SparseRetriever
from citely.retrieval.types import RetrievalResult

log = get_logger(__name__)


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
        rc = self._cfg.retrieval

        # Run both legs concurrently. (Query construction/translation + metadata filters
        # arrive in phase 6; for now both legs see the raw query.)
        sparse_list, dense_list = await asyncio.gather(
            self._sparse.retrieve(query, rc.bm25_top_n),
            self._dense.retrieve(query, rc.dense_top_n),
        )

        fused = reciprocal_rank_fusion([dense_list, sparse_list], k_rrf=rc.rrf_k)
        candidates = fused[: rc.rerank_candidates]

        # Sparse-only hits arrive without text/PaperRef — hydrate them once via the
        # dense leg's repository so the reranker has text and results render cleanly.
        missing = [p.passage_id for p in candidates if not p.text]
        if missing:
            hydrated = await self._dense.hydrate(missing)
            for passage in candidates:
                source = hydrated.get(passage.passage_id)
                if source is not None and not passage.text:
                    passage.text = source.text
                    passage.paper_id = source.paper_id
                    passage.paper = source.paper
        candidates = [p for p in candidates if p.text]

        reranked = await self._reranker.rerank(query, candidates, rc.final_k)
        for i, passage in enumerate(reranked, start=1):
            passage.source_key = f"S{i}"

        log.info(
            "retrieve.done",
            query=query,
            sparse=len(sparse_list),
            dense=len(dense_list),
            fused=len(fused),
            final=len(reranked),
        )
        return RetrievalResult(query=query, passages=reranked)
