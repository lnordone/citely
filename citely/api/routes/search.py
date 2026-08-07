"""POST /search — hybrid retrieval, returns ranked citation-keyed sources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from citely.api.deps import AppState, get_state, make_retriever, resolve_llm
from citely.api.schemas import SearchRequest, SearchResponse, to_sources_out
from citely.db.session import get_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(
    req: SearchRequest,
    state: AppState = Depends(get_state),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    # The retriever is built in the handler rather than injected because `req.model`
    # changes the wiring (the query constructor's LLM), and a dependency cannot see the
    # request body.
    retriever = make_retriever(state, session, resolve_llm(state, req.model))
    result = await retriever.retrieve(req.query)
    passages = result.passages[: req.top_k] if req.top_k else result.passages
    return SearchResponse(query=req.query, sources=to_sources_out(passages))
