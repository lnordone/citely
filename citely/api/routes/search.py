"""POST /search — hybrid retrieval, returns ranked citation-keyed sources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from citely.api.deps import AppState, build_retriever, get_db, get_state, resolve_llm
from citely.api.schemas import SearchRequest, SearchResponse, SourceOut

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(
    req: SearchRequest,
    state: AppState = Depends(get_state),
    session: AsyncSession = Depends(get_db),
) -> SearchResponse:
    llm = resolve_llm(state, req.model)
    retriever = build_retriever(state, session, llm)
    result = await retriever.retrieve(req.query)
    passages = result.passages[: req.top_k] if req.top_k else result.passages
    sources = [
        SourceOut(
            source_key=p.source_key,
            passage_id=p.passage_id,
            paper_id=p.paper_id,
            title=p.paper.title if p.paper else None,
            text=p.text,
            score=p.score,
        )
        for p in passages
    ]
    return SearchResponse(query=req.query, sources=sources)
