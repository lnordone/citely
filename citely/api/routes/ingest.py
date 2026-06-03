"""POST /ingest.

# TODO(phase 8): trigger the ingest pipeline; return counts.
"""

from __future__ import annotations

from fastapi import APIRouter

from citely.api.schemas import IngestRequest, IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest) -> IngestResponse:
    raise NotImplementedError  # TODO(phase 8)
