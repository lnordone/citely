"""POST /review (SSE streaming).

# TODO(phase 8): retrieve -> stream reviewer claims as SSE -> optional verify -> render.
"""

from __future__ import annotations

from fastapi import APIRouter

from citely.api.schemas import ReviewRequest

router = APIRouter()


@router.post("/review")
async def review(req: ReviewRequest) -> object:
    """Server-sent events stream of the cited review."""
    raise NotImplementedError  # TODO(phase 8)
