#!/usr/bin/env python
"""Sanity check for retrieval: each leg solo, RRF on hand inputs, filter holds.

Verifies:
  * the sparse (BM25) leg returns ranked hits for a query,
  * the dense (pgvector) leg returns ranked hits for a query,
  * RRF on hand-built lists rewards cross-list agreement (pure, no DB),
  * a metadata filter actually narrows the dense leg's results,
  * the full HybridRetriever runs end-to-end and assigns S-keys.

Requires a running DB with embedded passages (run scripts/check_index.py first) and the
local embedding + reranker models.

    python scripts/check_retrieval.py --query "graph neural networks"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from citely.config import load_config  # noqa: E402
from citely.db.repository import PassageRepository  # noqa: E402
from citely.db.session import dispose_db, get_session_factory, init_db  # noqa: E402
from citely.indexing.bm25_index import BM25Index  # noqa: E402
from citely.providers.factory import build_embedding_provider, build_reranker  # noqa: E402
from citely.retrieval.dense import DenseRetriever  # noqa: E402
from citely.retrieval.fusion import reciprocal_rank_fusion  # noqa: E402
from citely.retrieval.retriever import HybridRetriever  # noqa: E402
from citely.retrieval.sparse import SparseRetriever  # noqa: E402
from citely.retrieval.types import QueryFilters, RetrievedPassage  # noqa: E402
from citely.logging import configure_logging  # noqa: E402


def _p(pid: str) -> RetrievedPassage:
    return RetrievedPassage(passage_id=pid, paper_id=pid, text=pid, score=0.0)


def _check_rrf() -> bool:
    a = [_p("x"), _p("y"), _p("z")]
    b = [_p("y"), _p("x"), _p("w")]
    fused = reciprocal_rank_fusion([a, b], k_rrf=60)
    top2 = {fused[0].passage_id, fused[1].passage_id}
    print(f"[rrf] fused order = {[p.passage_id for p in fused]}  top2={top2}")
    ok = top2 == {"x", "y"}
    print(f"[rrf] agreement rewarded: {ok}")
    return ok


async def main_async(args: argparse.Namespace) -> int:
    configure_logging()
    cfg = load_config(args.config)
    init_db(cfg)
    provider = build_embedding_provider(cfg)

    print("=" * 70)
    print(f"query: {args.query!r}")
    print("=" * 70)

    ok = True

    factory = get_session_factory()
    async with factory() as session:
        repo = PassageRepository(session)
        passages = await repo.list_all()

        if not passages:
            print("\nFAIL: no passages (run scripts/check_index.py first)")
            await dispose_db()
            return 1

        # --- sparse leg solo ---
        index = BM25Index()
        index.build(passages)
        sparse = SparseRetriever(index)
        sparse_hits = await sparse.retrieve(args.query, top_n=5)
        print("\n[sparse top-5]")
        for r, p in enumerate(sparse_hits, 1):
            print(f"  {r}. {p.passage_id}  score={p.score:.3f}")
        ok = ok and bool(sparse_hits)

        # --- dense leg solo ---
        dense = DenseRetriever(provider, repo)
        dense_hits = await dense.retrieve(args.query, top_n=5)
        print("\n[dense top-5]")
        for r, p in enumerate(dense_hits, 1):
            title = p.paper.title[:60] if p.paper else "?"
            print(f"  {r}. {p.passage_id}  sim={p.score:.3f}  {title!r}")
        ok = ok and bool(dense_hits)

        # --- filter narrows results ---
        unfiltered = await dense.retrieve(args.query, top_n=100)
        future = QueryFilters(date_after=date(2999, 1, 1))
        filtered = await dense.retrieve(args.query, top_n=100, filters=future)
        print(f"\n[filter] dense unfiltered={len(unfiltered)} "
              f"date_after=2999 -> {len(filtered)}")
        narrows = len(filtered) < len(unfiltered) and len(filtered) == 0
        print(f"[filter] filter narrows results: {narrows}")
        ok = ok and narrows

    # --- RRF pure check ---
    print()
    ok = _check_rrf() and ok

    # --- full hybrid end-to-end (own session; loads reranker) ---
    print("\n[hybrid] running full pipeline (loads reranker) ...")
    async with factory() as session:
        repo = PassageRepository(session)
        index = BM25Index()
        index.build(await repo.list_all())
        hybrid = HybridRetriever(
            cfg,
            SparseRetriever(index),
            DenseRetriever(provider, repo),
            build_reranker(cfg),
        )
        result = await hybrid.retrieve(args.query)
    print(f"[hybrid] final_k={len(result.passages)}")
    for p in result.passages:
        title = p.paper.title[:55] if p.paper else "?"
        print(f"  [{p.source_key}] {p.passage_id}  rerank={p.score:.3f}  {title!r}")
    keys = [p.source_key for p in result.passages]
    keys_ok = keys == [f"S{i}" for i in range(1, len(result.passages) + 1)]
    print(f"[hybrid] source keys sequential: {keys_ok}")
    ok = ok and bool(result.passages) and keys_ok

    await dispose_db()
    print("\n" + "=" * 70)
    print(f"RETRIEVAL: {'PASS' if ok else 'FAIL'}")
    print("=" * 70)
    return 0 if ok else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=None)
    p.add_argument("--query", default="neural network representation learning")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(main_async(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
