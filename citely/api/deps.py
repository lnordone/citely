"""Dependency providers: get_db, get_llm, get_embedder, get_retriever, ...

Heavy singletons (providers, reranker, BM25 index, query constructor) are built once in
the app lifespan and stashed on ``app.state.citely`` as an :class:`AppState`. Routes pull
them through these dependencies and never instantiate clients directly. Per-request the
only thing built fresh is the :class:`HybridRetriever`, because its dense leg is bound to
the request-scoped DB session.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Depends, Request

from citely.db.repository import PassageRepository
from citely.db.session import get_session
from citely.retrieval.dense import DenseRetriever
from citely.retrieval.retriever import HybridRetriever
from citely.retrieval.sparse import SparseRetriever

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from citely.config import Config
    from citely.indexing.bm25_index import SparseIndex
    from citely.providers.base import EmbeddingProvider, LLMProvider
    from citely.query.construct import QueryConstructor
    from citely.retrieval.rerank import Reranker


@dataclass
class AppState:
    """Process-wide singletons populated in the API lifespan."""

    cfg: Config
    llm: LLMProvider
    embedder: EmbeddingProvider
    reranker: Reranker
    bm25_index: SparseIndex
    constructor: QueryConstructor


def get_state(request: Request) -> AppState:
    state: AppState = request.app.state.citely
    return state


def get_llm(request: Request) -> LLMProvider:
    return get_state(request).llm


def get_embedder(request: Request) -> EmbeddingProvider:
    return get_state(request).embedder


def get_retriever(
    request: Request, session: AsyncSession = Depends(get_session)
) -> HybridRetriever:
    state = get_state(request)
    repository = PassageRepository(session)
    return HybridRetriever(
        state.cfg,
        state.constructor,
        SparseRetriever(state.bm25_index),
        DenseRetriever(state.embedder, repository),
        state.reranker,
    )


def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session
