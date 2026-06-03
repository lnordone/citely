"""POST /search.

# TODO(phase 8): run HybridRetriever and return ranked, citation-keyed sources.
"""

from __future__ import annotations

from fastapi import APIRouter

from citely.api.schemas import SearchRequest, SearchResponse

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    raise NotImplementedError  # TODO(phase 8)
