"""HybridRetriever — orchestrates the whole retrieval pipeline.

construct -> {sparse, dense legs} -> RRF fusion -> rerank -> assign source keys -> final_k.
All sub-components (retrievers, reranker) are injected; providers reach it only via those.

"""

from __future__ import annotations

import asyncio

from citely.config import Config, FilterOrder
from citely.logging import get_logger
from citely.query.construct import QueryConstructor
from citely.retrieval.dense import DenseRetriever
from citely.retrieval.fusion import reciprocal_rank_fusion
from citely.retrieval.rerank import Reranker
from citely.retrieval.sparse import SparseRetriever
from citely.retrieval.types import RetrievalResult, RetrievedPassage

log = get_logger(__name__)


class HybridRetriever:
    def __init__(
        self,
        cfg: Config,
        constructor: QueryConstructor,
        sparse: SparseRetriever,
        dense: DenseRetriever,
        reranker: Reranker,
    ) -> None:
        self._cfg = cfg
        self._constructor = constructor
        self._sparse = sparse
        self._dense = dense
        self._reranker = reranker

    async def retrieve(self, query: str) -> RetrievalResult:
        rc = self._cfg.retrieval

        # construct -> filters + sparse/dense legs.
        cq = await self._constructor.construct(query)
        has_filters = not cq.filters.is_empty()
        # `pre` pushes filters into the dense SQL (better recall within the filter);
        # either way we re-check filters on the fused candidates below so sparse-only
        # hits also obey them.
        pre = rc.filter_order is FilterOrder.pre
        dense_filters = cq.filters if (pre and has_filters) else None

        # Sparse leg runs concurrently with the dense group, but the dense variants run
        # sequentially: they share one AsyncSession (and one embedding tokenizer), neither
        # of which is safe for concurrent use within a single request.
        async def _dense_legs() -> list[list[RetrievedPassage]]:
            return [
                await self._dense.retrieve(q, rc.dense_top_n, dense_filters)
                for q in cq.dense_queries
            ]

        sparse_list, dense_lists = await asyncio.gather(
            self._sparse.retrieve(cq.bm25_query, rc.bm25_top_n),
            _dense_legs(),
        )

        fused = reciprocal_rank_fusion([*dense_lists, sparse_list], k_rrf=rc.rrf_k)

        # Enforce filters across all legs (covers sparse-only hits and `post` mode).
        if has_filters:
            allowed = await self._dense.filter_ids([p.passage_id for p in fused], cq.filters)
            fused = [p for p in fused if p.passage_id in allowed]

        candidates = fused[: rc.rerank_candidates]
        candidates = await self._hydrate_missing(candidates)

        reranked = await self._reranker.rerank(query, candidates, rc.final_k)
        for i, passage in enumerate(reranked, start=1):
            passage.source_key = f"S{i}"

        log.info(
            "retrieve.done",
            query=query,
            variants=len(cq.dense_queries),
            filters=not cq.filters.is_empty(),
            sparse=len(sparse_list),
            fused=len(fused),
            final=len(reranked),
        )
        return RetrievalResult(query=query, passages=reranked)

    async def _hydrate_missing(
        self, candidates: list[RetrievedPassage]
    ) -> list[RetrievedPassage]:
        """Fill text/PaperRef for sparse-only hits, then drop any still without text."""
        missing = [p.passage_id for p in candidates if not p.text]
        if missing:
            hydrated = await self._dense.hydrate(missing)
            for passage in candidates:
                source = hydrated.get(passage.passage_id)
                if source is not None and not passage.text:
                    passage.text = source.text
                    passage.paper_id = source.paper_id
                    passage.paper = source.paper
        return [p for p in candidates if p.text]
