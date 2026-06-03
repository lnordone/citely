"""Async engine + session factory.

# TODO(phase 2): implement engine creation, session factory, and startup dimension check.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from citely.config import Config

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


def create_engine(cfg: Config) -> AsyncEngine:
    """Create the async SQLAlchemy engine from cfg.db.url."""
    raise NotImplementedError  # TODO(phase 2)


def create_session_factory(engine: AsyncEngine):  # noqa: ANN201
    """Return an async_sessionmaker bound to ``engine``."""
    raise NotImplementedError  # TODO(phase 2)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an ``AsyncSession`` (FastAPI dependency)."""
    raise NotImplementedError  # TODO(phase 2)
    yield  # pragma: no cover - keeps this a valid async generator
