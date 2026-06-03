"""CLI: embed all un-embedded passages into the vector index.

    python -m citely.indexing            # embed everything outstanding
    python -m citely.indexing --batch 256

BM25 is an in-process sparse index built at retrieval time, so this command only
materializes the dense (and optional int8) vectors that persist in the database.
"""

from __future__ import annotations

import argparse
import asyncio

from citely.config import load_config
from citely.db.session import dispose_db, init_db
from citely.indexing.embedder import build_embedder
from citely.logging import configure_logging, get_logger
from citely.providers.factory import build_embedding_provider

log = get_logger(__name__)


async def main_async(args: argparse.Namespace) -> int:
    configure_logging()
    cfg = load_config(args.config)
    init_db(cfg)
    try:
        provider = build_embedding_provider(cfg)
        embedder = build_embedder(cfg, provider, batch_size=args.batch)
        written = await embedder.index_all()
    finally:
        await dispose_db()
    log.info("index.complete", written=written)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=None)
    p.add_argument("--batch", type=int, default=128, help="embedding batch size")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(main_async(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
