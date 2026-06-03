"""Data access only — no business logic. PaperRepository, PassageRepository.

# TODO(phase 2): implement CRUD + dense (pgvector) query helpers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from citely.db.models import Paper, Passage


class PaperRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, paper: Paper) -> None:
        raise NotImplementedError  # TODO(phase 2)

    async def get(self, paper_id: str) -> Paper | None:
        raise NotImplementedError  # TODO(phase 2)

    async def count(self) -> int:
        raise NotImplementedError  # TODO(phase 2)


class PassageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_upsert(self, passages: list[Passage]) -> None:
        raise NotImplementedError  # TODO(phase 2)

    async def get(self, passage_id: str) -> Passage | None:
        raise NotImplementedError  # TODO(phase 2)

    async def list_all(self) -> list[Passage]:
        raise NotImplementedError  # TODO(phase 4)

    async def search_dense(
        self, embedding: list[float], top_n: int, filters: object | None = None
    ) -> list[tuple[str, float]]:
        """Return [(passage_id, distance)] via pgvector cosine."""
        raise NotImplementedError  # TODO(phase 5)
