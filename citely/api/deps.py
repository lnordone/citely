"""Dependency providers: get_db, get_llm, get_embedder, get_retriever, ...

Heavy singletons (providers, reranker, BM25 index, query constructor) are built once in
the app lifespan and stashed on ``app.state.citely`` as an :class:`AppState`. Routes pull
them through these dependencies and never instantiate clients directly. Per-request the
only thing built fresh is the :class:`HybridRetriever`, because its dense leg is bound to
the request-scoped DB session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import Depends, Request

from citely.db.repository import PassageRepository
from citely.db.session import get_session
from citely.providers.factory import build_llm_provider
from citely.query.construct import build_query_constructor
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
    # Providers built for per-request model overrides, keyed by model name. Providers are
    # thin stateless clients, but caching keeps a hot model from rebuilding per request.
    llm_overrides: dict[str, LLMProvider] = field(default_factory=dict)


def get_state(request: Request) -> AppState:
    state: AppState = request.app.state.citely
    return state


def resolve_llm(state: AppState, model: str | None) -> LLMProvider:
    """Return the LLM for this request, honouring an optional model override.

    The configured *provider* never changes per request — only which model it is asked
    for. An unknown model is not validated here; it surfaces as an error from the
    provider at call time (validating would cost a round trip on every request).
    """
    if not model or model == state.llm.model_name:
        return state.llm
    cached = state.llm_overrides.get(model)
    if cached is None:
        cached = build_llm_provider(state.cfg, model)
        state.llm_overrides[model] = cached
    return cached


def make_retriever(
    state: AppState, session: AsyncSession, llm: LLMProvider | None = None
) -> HybridRetriever:
    """Wire a request-scoped HybridRetriever.

    Only the query constructor depends on the LLM, so an override rebuilds just that;
    the reranker, BM25 index and embedder stay the shared singletons.
    """
    constructor = (
        state.constructor
        if llm is None or llm is state.llm
        else build_query_constructor(llm, state.cfg)
    )
    return HybridRetriever(
        state.cfg,
        constructor,
        SparseRetriever(state.bm25_index),
        DenseRetriever(state.embedder, PassageRepository(session)),
        state.reranker,
    )


def get_llm(request: Request) -> LLMProvider:
    return get_state(request).llm


def get_embedder(request: Request) -> EmbeddingProvider:
    return get_state(request).embedder


def get_retriever(
    request: Request, session: AsyncSession = Depends(get_session)
) -> HybridRetriever:
    """Default-config retriever. Routes accepting a ``model`` override call
    :func:`make_retriever` directly instead, since the wiring depends on the body."""
    return make_retriever(get_state(request), session)


def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session
