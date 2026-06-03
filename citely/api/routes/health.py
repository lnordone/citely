"""GET /health.

# TODO(phase 8): report provider model names and db connectivity.
"""

from __future__ import annotations

from fastapi import APIRouter

from citely.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    raise NotImplementedError  # TODO(phase 8)
