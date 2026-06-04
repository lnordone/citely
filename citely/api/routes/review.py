"""POST /review (SSE streaming).

Retrieves sources, streams each grounded claim as it is produced (optionally verified),
then emits a final ``done`` event carrying the fully rendered markdown review.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from citely.api.deps import AppState, build_retriever, get_db, get_state, resolve_llm
from citely.api.schemas import ReviewRequest
from citely.generation.render import render_markdown
from citely.generation.reviewer import ReviewGenerator
from citely.generation.verifier import ClaimVerifier
from citely.retrieval.types import Claim

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/review")
async def review(
    req: ReviewRequest,
    state: AppState = Depends(get_state),
    session: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """Server-sent events stream of the cited review."""
    llm = resolve_llm(state, req.model)
    retriever = build_retriever(state, session, llm)
    result = await retriever.retrieve(req.query)
    sources = result.passages
    reviewer = ReviewGenerator(llm, state.cfg)
    verifier = ClaimVerifier(llm, enabled=state.cfg.generation.verify_claims)

    async def event_generator() -> AsyncIterator[dict]:
        claims: list[Claim] = []
        async for claim in reviewer.generate(req.query, sources):
            claim = await verifier.verify(claim, sources)
            claims.append(claim)
            yield {
                "event": "claim",
                "data": json.dumps(
                    {
                        "text": claim.text,
                        "source_ids": claim.source_ids,
                        "supported": claim.supported,
                    }
                ),
            }
        yield {
            "event": "done",
            "data": json.dumps(
                {"markdown": render_markdown(claims, sources), "num_claims": len(claims)}
            ),
        }

    return EventSourceResponse(event_generator())
