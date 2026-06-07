"""POST /review (SSE streaming).

Retrieves sources, streams each grounded claim as it is produced (optionally verified),
then emits a final ``done`` event carrying the fully rendered markdown review.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from citely.api.deps import get_retriever, get_state
from citely.api.schemas import ReviewRequest
from citely.generation.render import render_markdown
from citely.generation.reviewer import ReviewGenerator
from citely.generation.verifier import ClaimVerifier
from citely.retrieval.retriever import HybridRetriever
from citely.retrieval.types import Claim

router = APIRouter()


@router.post("/review")
async def review(
    req: ReviewRequest,
    request: Request,
    retriever: HybridRetriever = Depends(get_retriever),
) -> EventSourceResponse:
    """Server-sent events stream of the cited review."""
    state = get_state(request)
    result = await retriever.retrieve(req.query)
    sources = result.passages
    reviewer = ReviewGenerator(state.llm, state.cfg)
    verifier = ClaimVerifier(state.llm, enabled=state.cfg.generation.verify_claims)

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
