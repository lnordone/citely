#!/usr/bin/env python
"""Sanity check for ingest: counts, idempotency, parent linkage.

Runs a small ingest twice against the configured database and verifies:
  * the second run does not grow the row counts (idempotent dedup on arxiv id),
  * every passage links to a real paper (no orphans).

Requires a running database (``make up`` / ``make migrate``) and network access to the
arXiv API. Uses a tiny ``--max`` so it is quick.

    python scripts/check_ingest.py
    python scripts/check_ingest.py --categories cs.AI --max 5
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402

from citely.config import load_config  # noqa: E402
from citely.db.models import Paper, Passage  # noqa: E402
from citely.db.session import dispose_db, get_session_factory, init_db  # noqa: E402
from citely.ingest.pipeline import run_ingest  # noqa: E402
from citely.logging import configure_logging  # noqa: E402


async def _counts() -> tuple[int, int, int]:
    """Return (papers, passages, orphan_passages)."""
    factory = get_session_factory()
    async with factory() as session:
        papers = (await session.execute(select(func.count()).select_from(Paper))).scalar_one()
        passages = (
            await session.execute(select(func.count()).select_from(Passage))
        ).scalar_one()
        orphans = (
            await session.execute(
                select(func.count())
                .select_from(Passage)
                .outerjoin(Paper, Passage.paper_id == Paper.id)
                .where(Paper.id.is_(None))
            )
        ).scalar_one()
    return int(papers), int(passages), int(orphans)


async def main_async(args: argparse.Namespace) -> int:
    configure_logging()
    cfg = load_config(args.config)
    init_db(cfg)

    print("=" * 70)
    print(f"categories : {args.categories or cfg.ingest.categories}")
    print(f"max papers : {args.max_papers}")
    print("=" * 70)

    print("\n[run 1] ingesting ...")
    s1 = await run_ingest(cfg, args.categories, args.max_papers)
    p1, pas1, orph1 = await _counts()
    print(f"[run 1] stored papers={s1.papers_stored} passages={s1.passages_stored}")
    print(f"[db   ] papers={p1} passages={pas1} orphans={orph1}")

    print("\n[run 2] re-ingesting (must be idempotent) ...")
    await run_ingest(cfg, args.categories, args.max_papers)
    p2, pas2, orph2 = await _counts()
    print(f"[db   ] papers={p2} passages={pas2} orphans={orph2}")

    await dispose_db()

    ok = True
    if p1 == 0:
        print("\nFAIL: no papers ingested (network/arXiv issue?)")
        ok = False
    if (p1, pas1) != (p2, pas2):
        print(f"\nFAIL: not idempotent — counts changed {(p1, pas1)} -> {(p2, pas2)}")
        ok = False
    if orph1 or orph2:
        print(f"\nFAIL: orphan passages detected ({orph1}, {orph2})")
        ok = False

    print("\n" + "=" * 70)
    print(f"INGEST: {'PASS' if ok else 'FAIL'}")
    print("=" * 70)
    return 0 if ok else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default=None)
    p.add_argument("--categories", nargs="+", default=["cs.AI"])
    p.add_argument("--max", type=int, default=5, dest="max_papers")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(main_async(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
