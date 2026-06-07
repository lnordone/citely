"""CLI: python -m citely.ingest --categories cs.* eess.* --max 50000

Fetches arXiv records for the given categories (wildcards allowed, e.g. ``cs.*`` for all
of computer science, ``eess.*`` for electrical engineering & systems science), chunks
abstracts, and stores everything. Idempotent — safe to re-run.
"""

from __future__ import annotations

import argparse
import asyncio

from citely.config import load_config
from citely.ingest.pipeline import run_ingest
from citely.logging import configure_logging
from citely.providers.factory import build_embedding_provider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="citely.ingest")
    parser.add_argument(
        "--categories",
        nargs="+",
        default=None,
        help="arXiv categories (wildcards ok), e.g. cs.* eess.*",
    )
    parser.add_argument("--max", type=int, default=None, dest="max_papers")
    parser.add_argument("--config", default=None)
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="store passages only; skip embedding (run `make index` later)",
    )
    args = parser.parse_args(argv)

    configure_logging()
    cfg = load_config(args.config)
    embedder = None if args.no_embed else build_embedding_provider(cfg)
    stats = asyncio.run(run_ingest(cfg, args.categories, args.max_papers, embedder=embedder))

    print(
        f"ingest complete: seen={stats.papers_seen} "
        f"papers_stored={stats.papers_stored} passages_stored={stats.passages_stored} "
        f"passages_embedded={stats.passages_embedded}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
