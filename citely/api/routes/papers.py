"""GET /papers — paginated listing of ingested papers with passage + embedding counts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query

from citely.api.deps import get_db
from citely.api.schemas import PaperOut, PapersResponse
from citely.db.repository import PaperRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/papers", response_model=PapersResponse)
async def list_papers(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> PapersResponse:
    """List ingested papers with per-paper passage and embedding counts."""
    pairs, total = await PaperRepository(session).list_with_counts(
        limit=limit,
        offset=offset,
        search=search or None,
    )
    return PapersResponse(
        papers=[
            PaperOut(
                id=paper.id,
                title=paper.title,
                authors=paper.authors,
                categories=paper.categories,
                published=paper.published,
                pdf_url=paper.pdf_url,
                ingested_at=paper.ingested_at,
                passage_count=passage_count,
                embedded_count=embedded_count,
            )
            for paper, passage_count, embedded_count in pairs
        ],
        total=total,
    )
