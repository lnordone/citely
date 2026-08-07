"""POST /review (SSE streaming).

Retrieves sources, emits the source set the review is grounded in, then streams each
grounded claim as it is produced (optionally verified), then a final ``done`` event
carrying the fully rendered markdown review.

The ``sources`` event is what makes the citation keys trustworthy: ``S1``..``Sn`` are
assigned per retrieval, so a client resolving them against a *separate* ``/search`` call
could label a citation with a paper this review never cited. Every key in this stream
refers to the source list emitted here.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from citely.api.deps import AppState, get_state, make_retriever, resolve_llm
from citely.api.schemas import ReviewRequest, to_sources_out
from citely.db.session import get_session
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
    session: AsyncSession = Depends(get_session),
) -> EventSourceResponse:
    """Server-sent events stream of the cited review."""
    llm = resolve_llm(state, req.model)
    retriever = make_retriever(state, session, llm)
    # Retrieval stays outside the generator: the retriever's dense leg holds the
    # request-scoped DB session, which FastAPI tears down once the endpoint returns and
    # the response begins streaming. A retrieval failure is therefore still a plain 500,
    # raised before the stream opens. The generator below touches no DB.
    result = await retriever.retrieve(req.query)
    sources = result.passages
    reviewer = ReviewGenerator(llm, state.cfg)
    verifier = ClaimVerifier(llm, enabled=state.cfg.generation.verify_claims)

    async def event_generator() -> AsyncIterator[dict]:
        payload = [s.model_dump() for s in to_sources_out(sources)]
        yield {"event": "sources", "data": json.dumps({"sources": payload})}

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
