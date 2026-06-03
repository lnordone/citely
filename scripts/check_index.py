#!/usr/bin/env python
"""Sanity check for indexing: null/zero vectors, raw semantic top-5, int8 vs full.

Embeds all un-embedded passages, then verifies:
  * every passage has a non-null, non-zero embedding,
  * a sample query returns a sensible semantic top-5 (eyeball),
  * the int8-quantized vectors rank near-identically to full precision.

Also builds the BM25 index and runs a sample sparse query.

Requires a running database with ingested passages (run scripts/check_ingest.py or
`make ingest` first) and the local embedding model.

    python scripts/check_index.py --query "graph neural networks"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from citely.config import load_config  # noqa: E402
from citely.db.repository import PassageRepository  # noqa: E402
from citely.db.session import dispose_db, get_session_factory, init_db  # noqa: E402
from citely.indexing.bm25_index import BM25Index  # noqa: E402
from citely.indexing.embedder import build_embedder  # noqa: E402
from citely.indexing.quantize import dequantize_int8  # noqa: E402
from citely.logging import configure_logging  # noqa: E402
from citely.providers.factory import build_embedding_provider  # noqa: E402


def _cosine_top_k(query: np.ndarray, matrix: np.ndarray, k: int) -> list[int]:
    """Indices of the top-k rows of ``matrix`` by cosine similarity to ``query``."""
    def _norm(m: np.ndarray) -> np.ndarray:
        return m / (np.linalg.norm(m, axis=-1, keepdims=True) + 1e-12)

    sims = _norm(matrix) @ _norm(query.reshape(1, -1)).ravel()
    return list(np.argsort(sims)[::-1][:k])


async def main_async(args: argparse.Namespace) -> int:
    configure_logging()
    cfg = load_config(args.config)
    init_db(cfg)

    provider = build_embedding_provider(cfg)

    print("=" * 70)
    print(f"embedding model : {provider.model_name}")
    print(f"query           : {args.query!r}")
    print("=" * 70)

    print("\n[embed] indexing un-embedded passages ...")
    written = await build_embedder(cfg, provider).index_all()
    print(f"[embed] wrote {written} embeddings this run")

    factory = get_session_factory()
    async with factory() as session:
        passages = await PassageRepository(session).list_all()

    if not passages:
        print("\nFAIL: no passages in db (run scripts/check_ingest.py first)")
        await dispose_db()
        return 1

    ok = True

    # 1) No null/zero embeddings.
    null_ids = [p.id for p in passages if p.embedding is None]
    full = np.array([list(p.embedding) for p in passages if p.embedding is not None], dtype=np.float32)
    zero_norm = int(np.sum(np.linalg.norm(full, axis=1) == 0)) if len(full) else 0
    print(f"\n[vectors] passages={len(passages)} null={len(null_ids)} zero_norm={zero_norm}")
    if null_ids or zero_norm:
        ok = False
        print("FAIL: null or zero embeddings present")

    embedded = [p for p in passages if p.embedding is not None]

    # 2) Semantic top-5 (eyeball).
    qvec = np.array((await provider.embed([args.query]))[0], dtype=np.float32)
    top = _cosine_top_k(qvec, full, min(5, len(full)))
    print("\n[semantic top-5]")
    for rank, i in enumerate(top, 1):
        print(f"  {rank}. {embedded[i].id}  {embedded[i].text[:90]!r}")

    # 3) int8 vs full ranking.
    have_i8 = [p for p in embedded if p.embedding_i8 is not None]
    if have_i8:
        i8 = np.array([dequantize_int8(p.embedding_i8) for p in have_i8], dtype=np.float32)
        full_sub = np.array([list(p.embedding) for p in have_i8], dtype=np.float32)
        k = min(5, len(have_i8))
        top_full = _cosine_top_k(qvec, full_sub, k)
        top_i8 = _cosine_top_k(qvec, i8, k)
        overlap = len(set(top_full) & set(top_i8)) / k
        max_abs_err = float(np.max(np.abs(i8 - full_sub)))
        print(f"\n[int8] coverage={len(have_i8)}/{len(embedded)} "
              f"top{k}_overlap={overlap:.2f} max_abs_err={max_abs_err:.4f}")
        if overlap < 0.8:
            ok = False
            print("FAIL: int8 ranking diverges from full precision (overlap < 0.8)")
    else:
        print("\n[int8] no quantized vectors (config.indexing.quantization != int8)")

    # 4) BM25 sparse index smoke test.
    index = BM25Index()
    index.build(passages)
    sparse_hits = index.search(args.query, top_n=5)
    print("\n[bm25 top-5]")
    for rank, (pid, score) in enumerate(sparse_hits, 1):
        print(f"  {rank}. {pid}  score={score:.3f}")
    if not sparse_hits:
        ok = False
        print("FAIL: BM25 returned no hits")

    await dispose_db()
    print("\n" + "=" * 70)
    print(f"INDEX: {'PASS' if ok else 'FAIL'}")
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
