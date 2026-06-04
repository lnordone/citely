"""POST /ingest — trigger the ingest pipeline; return counts."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from citely.api.deps import AppState, get_state
from citely.api.schemas import IngestRequest, IngestResponse
from citely.ingest.pipeline import run_ingest

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    req: IngestRequest,
    state: AppState = Depends(get_state),
) -> IngestResponse:
    stats = await run_ingest(state.cfg, req.categories, req.max_papers)
    return IngestResponse(
        papers_stored=stats.papers_stored,
        passages_stored=stats.passages_stored,
    )
