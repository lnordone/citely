"""POST /ingest — trigger the ingest pipeline; return counts."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from citely.api.deps import AppState, get_state
from citely.api.schemas import IngestRequest
from citely.db.repository import PassageRepository
from citely.db.session import get_session_factory
from citely.ingest.arxiv_client import ArxivRateLimitError
from citely.ingest.pipeline import stream_ingest
from citely.logging import get_logger

router = APIRouter()
log = get_logger(__name__)


@router.post("/ingest")
async def ingest(
    req: IngestRequest,
    state: AppState = Depends(get_state),
) -> EventSourceResponse:
    """SSE stream of ingestion progress, then a final ``done`` event.

    Events:
    - ``progress`` — ``{phase, papers?, passages?, max_papers?, embedded?, total?}``
    - ``done``     — ``{papers_stored, passages_stored, passages_embedded}``
    - ``error``    — ``{message}`` (e.g. arXiv rate-limit exhausted)
    """

    async def event_generator() -> AsyncIterator[dict]:
        try:
            async for progress in stream_ingest(
                state.cfg, req.categories, req.max_papers, embedder=state.embedder
            ):
                phase = progress.get("phase")
                if phase == "done":
                    # Rebuild the in-process BM25 index so new passages are immediately
                    # reachable via the sparse leg without restarting the server.
                    if progress.get("passages_stored", 0):
                        factory = get_session_factory()
                        async with factory() as session:
                            all_passages = await PassageRepository(session).list_all()
                        state.bm25_index.build(all_passages)
                    yield {"event": "done", "data": json.dumps(progress)}
                else:
                    yield {"event": "progress", "data": json.dumps(progress)}
        except ArxivRateLimitError as exc:
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
        except Exception as exc:
            log.error("ingest.stream_error", error=str(exc))
            yield {"event": "error", "data": json.dumps({"message": f"Ingest failed: {exc}"})}

    return EventSourceResponse(event_generator())
