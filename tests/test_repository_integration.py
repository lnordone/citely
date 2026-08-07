"""PaperRepository against a real Postgres.

These cover behaviour that only exists in the database — ``INSERT ... ON CONFLICT``
semantics, JSON column round-tripping, and LIMIT/OFFSET ordering stability — so they are
skipped unless a migrated Citely database is reachable. Bring one up with::

    docker compose up -d --wait db && alembic upgrade head

Each test runs inside a transaction that is rolled back, so the database is left clean.
"""

from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import text

from citely.config import load_config
from citely.db.models import Paper
from citely.db.repository import PaperRepository
from citely.db.session import create_engine, create_session_factory

pytestmark = pytest.mark.integration


async def _engine_or_skip():
    try:
        cfg = load_config()
    except FileNotFoundError:  # pragma: no cover - config-less checkout
        pytest.skip("no config.yaml; skipping DB integration tests")
    engine = create_engine(cfg)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1 FROM papers LIMIT 1"))
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"no migrated Citely database reachable ({type(exc).__name__})")
    return engine


@pytest_asyncio.fixture
async def session():
    """A session whose work is always rolled back."""
    engine = await _engine_or_skip()
    factory = create_session_factory(engine)
    async with factory() as s:
        try:
            yield s
        finally:
            await s.rollback()
    await engine.dispose()


def _paper(pid: str, title: str = "T", published: date = date(2024, 1, 2)) -> Paper:
    return Paper(
        id=pid,
        title=title,
        authors=["Ada Lovelace"],
        abstract="An abstract.",
        categories=["cs.LG", "cs.AI"],
        published=published,
        pdf_url=f"https://arxiv.org/pdf/{pid}",
    )


async def test_upsert_reports_new_then_existing(session):
    """The pipeline's skip logic depends entirely on this return value."""
    repo = PaperRepository(session)
    assert await repo.upsert(_paper("test.0001")) is True
    assert await repo.upsert(_paper("test.0001")) is False


async def test_upsert_refreshes_metadata_but_keeps_first_seen_timestamp(session):
    repo = PaperRepository(session)
    await repo.upsert(_paper("test.0002", title="Original"))
    await session.flush()
    first = await repo.get("test.0002")
    first_seen = first.ingested_at

    await repo.upsert(_paper("test.0002", title="Revised"))
    await session.flush()
    session.expire_all()

    refreshed = await repo.get("test.0002")
    assert refreshed.title == "Revised"
    assert refreshed.ingested_at == first_seen


async def test_json_columns_round_trip(session):
    repo = PaperRepository(session)
    await repo.upsert(_paper("test.0003"))
    await session.flush()
    session.expire_all()

    stored = await repo.get("test.0003")
    assert stored.authors == ["Ada Lovelace"]
    assert stored.categories == ["cs.LG", "cs.AI"]


async def test_pagination_is_stable_when_a_reingest_touches_rows_mid_paging(session):
    """A bulk ingest gives many papers the same ``ingested_at``, so ordering on that
    column alone is a *partial* order and LIMIT/OFFSET over it is not stable.

    The trigger is ordinary: re-running ingest updates existing papers' metadata, and an
    UPDATE writes a new tuple at the end of the heap, changing the physical order a seq
    scan returns. If the user is paging the library while that happens, a row already
    shown on page 1 slides onto page 2 and the row it displaced is never seen. A unique
    tiebreaker in the ORDER BY makes the order total, so paging stays consistent.
    """
    repo = PaperRepository(session)
    ids = [f"test.pag{i:03d}" for i in range(25)]
    for pid in ids:
        await repo.upsert(_paper(pid))
    await session.flush()

    def page(rows) -> list[str]:
        return [paper.id for paper, _pc, _ec in rows]

    first, total = await repo.list_with_counts(limit=10, offset=0)
    assert total >= 25
    seen = page(first)

    # A concurrent re-ingest refreshing metadata on papers the user already paged past.
    for pid in seen[:3]:
        await repo.upsert(_paper(pid, title="Refreshed"))
    await session.flush()

    for offset in (10, 20):
        rows, _ = await repo.list_with_counts(limit=10, offset=offset)
        seen.extend(page(rows))

    paged = [pid for pid in seen if pid.startswith("test.pag")]
    assert len(paged) == len(set(paged)), "a paper appeared on two pages"
    assert set(paged) == set(ids), "a paper was missed by pagination"


async def test_list_with_counts_filters_by_title(session):
    repo = PaperRepository(session)
    await repo.upsert(_paper("test.0004", title="Sparse Attention Mechanisms"))
    await session.flush()

    rows, total = await repo.list_with_counts(search="sparse attention")
    assert total >= 1
    assert any(paper.id == "test.0004" for paper, _pc, _ec in rows)
