"""Async engine + session factory.

A single process-wide engine + ``async_sessionmaker`` is built lazily and reused
everywhere (CLIs, scripts, and—wired in phase 8—the API lifespan). ``get_session`` is the
unit-of-work dependency: it yields exactly one session and guarantees cleanup.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from citely.config import Config, get_config
from citely.db.models import EMBEDDING_DIM
from citely.logging import get_logger

if TYPE_CHECKING:
    from citely.providers.base import EmbeddingProvider

log = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine(cfg: Config, *, echo: bool = False) -> AsyncEngine:
    """Create the async SQLAlchemy engine from ``cfg.db.url``.

    The URL must use an async driver (``postgresql+asyncpg://...``). ``pool_pre_ping``
    avoids handing out connections the server has already dropped.
    """
    return create_async_engine(cfg.db.url, echo=echo, pool_pre_ping=True, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an ``async_sessionmaker`` bound to ``engine``.

    ``expire_on_commit=False`` keeps loaded attributes usable after ``commit()`` so
    callers can read returned objects without triggering a fresh (and, here, illegal
    sync) lazy-load.
    """
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def init_db(
    cfg: Config | None = None, *, echo: bool = False
) -> async_sessionmaker[AsyncSession]:
    """Idempotently build the process-wide engine + session factory and return it."""
    global _engine, _session_factory
    if _session_factory is None:
        cfg = cfg or get_config()
        _engine = create_engine(cfg, echo=echo)
        _session_factory = create_session_factory(_engine)
        log.info("db.engine_initialized", url=_redact(cfg.db.url))
    return _session_factory


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory, building it on first use."""
    if _session_factory is None:
        return init_db()
    return _session_factory


async def dispose_db() -> None:
    """Dispose the engine and reset module state (call on shutdown / in tests)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` (FastAPI dependency).

    One session per call; rolled back and closed on exit. Callers own the transaction
    boundary (i.e. they decide when to ``commit``).
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def check_embedding_dimension(
    provider: EmbeddingProvider, expected: int = EMBEDDING_DIM
) -> None:
    """Assert the provider's vector width matches the pgvector column width.

    A mismatch is a hard error: every insert/query against ``passages.embedding`` would
    otherwise be silently wrong. Call this at startup (API lifespan, ingest/index CLIs).
    """
    declared = provider.dimension
    if declared != expected:
        raise RuntimeError(
            f"Embedding dimension mismatch: provider {provider.model_name!r} reports "
            f"{declared}, but the pgvector column is {expected}. Update EMBEDDING_DIM "
            f"(and migrate) or switch embedding models."
        )
    log.info("db.dimension_check_ok", dimension=declared, model=provider.model_name)


def _redact(url: str) -> str:
    """Hide credentials in a DB URL before logging it."""
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    _, host = rest.split("@", 1)
    return f"{scheme}://***@{host}"
