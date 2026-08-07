"""FastAPI app factory + lifespan (db + providers) + DI wiring.

The lifespan builds every heavy singleton exactly once: LLM/embedding providers and the
cross-encoder reranker (via the provider factory), the query constructor, and an
in-process BM25 index over the currently-indexed passages. It also asserts the embedding
dimension against the pgvector column before serving, and disposes the DB engine on
shutdown.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from citely.api.deps import AppState
from citely.api.routes import health, ingest, models, papers, review, search
from citely.config import get_config
from citely.db.repository import PassageRepository
from citely.db.session import check_embedding_dimension, dispose_db, init_db
from citely.indexing.bm25_index import BM25Index
from citely.logging import configure_logging, get_logger
from citely.providers.factory import (
    build_embedding_provider,
    build_llm_provider,
    build_reranker,
)
from citely.query.construct import build_query_constructor

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    cfg = get_config()

    llm = build_llm_provider(cfg)
    embedder = build_embedding_provider(cfg)
    reranker = build_reranker(cfg)
    check_embedding_dimension(embedder)

    factory = init_db(cfg)
    bm25_index = BM25Index()
    async with factory() as session:
        passages = await PassageRepository(session).list_all()
    bm25_index.build(passages)

    app.state.citely = AppState(
        cfg=cfg,
        llm=llm,
        embedder=embedder,
        reranker=reranker,
        bm25_index=bm25_index,
        constructor=build_query_constructor(llm, cfg),
    )
    log.info(
        "api.startup",
        llm=llm.model_name,
        embedder=embedder.model_name,
        passages=len(passages),
    )
    try:
        yield
    finally:
        await dispose_db()


def create_app() -> FastAPI:
    """Application factory (referenced by `uvicorn ... --factory`)."""
    app = FastAPI(title="Citely", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(models.router)
    app.include_router(papers.router)
    app.include_router(search.router)
    app.include_router(review.router)
    return app
