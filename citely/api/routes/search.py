"""POST /search — hybrid retrieval, returns ranked citation-keyed sources."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from citely.api.deps import get_retriever
from citely.api.schemas import SearchRequest, SearchResponse, SourceOut
from citely.retrieval.retriever import HybridRetriever

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(
    req: SearchRequest,
    retriever: HybridRetriever = Depends(get_retriever),
) -> SearchResponse:
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
