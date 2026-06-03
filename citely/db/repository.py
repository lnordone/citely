"""Data access only — no business logic. PaperRepository, PassageRepository.

Repositories receive an ``AsyncSession`` and do NOT own the transaction: callers decide
when to ``commit``, so multiple operations can compose into one unit of work. Writes are
idempotent (``INSERT ... ON CONFLICT DO UPDATE``) so re-ingesting the same content does
not duplicate rows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from citely.db.models import Paper, Passage

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _paper_values(paper: Paper) -> dict:
    return {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "categories": paper.categories,
        "published": paper.published,
        "pdf_url": paper.pdf_url,
    }


def _passage_values(passage: Passage) -> dict:
    return {
        "id": passage.id,
        "paper_id": passage.paper_id,
        "chunk_index": passage.chunk_index,
        "text": passage.text,
        "embedding": passage.embedding,
        "embedding_i8": passage.embedding_i8,
    }


class PaperRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, paper: Paper) -> None:
        values = _paper_values(paper)
        stmt = pg_insert(Paper).values(**values)
        # On conflict, refresh mutable metadata but preserve first-seen ``ingested_at``
        # (it is never part of ``values``, so the existing row keeps its timestamp).
        update_cols = {c: stmt.excluded[c] for c in values if c != "id"}
        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols)
        await self._session.execute(stmt)

    async def get(self, paper_id: str) -> Paper | None:
        return await self._session.get(Paper, paper_id)

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(Paper))
        return int(result.scalar_one())


class PassageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_upsert(self, passages: list[Passage]) -> None:
        if not passages:
            return
        rows = [_passage_values(p) for p in passages]
        stmt = pg_insert(Passage).values(rows)
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "paper_id": excluded.paper_id,
                "chunk_index": excluded.chunk_index,
                "text": excluded.text,
                # Preserve an existing vector on re-ingest (phase-3 passages carry no
                # embedding); only overwrite when the incoming row supplies one (the
                # phase-4 embedder re-upserts with vectors populated).
                "embedding": func.coalesce(excluded.embedding, Passage.embedding),
                "embedding_i8": func.coalesce(
                    excluded.embedding_i8, Passage.embedding_i8
                ),
            },
        )
        await self._session.execute(stmt)

    async def get(self, passage_id: str) -> Passage | None:
        return await self._session.get(Passage, passage_id)

    async def list_all(self) -> list[Passage]:
        raise NotImplementedError  # TODO(phase 4)

    async def search_dense(
        self, embedding: list[float], top_n: int, filters: object | None = None
    ) -> list[tuple[str, float]]:
        """Return [(passage_id, distance)] via pgvector cosine."""
        raise NotImplementedError  # TODO(phase 5)
