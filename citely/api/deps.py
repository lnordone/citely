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

from citely.config import LLMProviderKind
from citely.db.repository import PassageRepository
from citely.db.session import get_session
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
    # Per-model LLM providers built on demand for request-level model overrides. Ollama
    # providers are cheap (HTTP only, no weights), so caching just avoids re-allocating.
    llm_cache: dict[str, LLMProvider] = field(default_factory=dict)


def get_state(request: Request) -> AppState:
    state: AppState = request.app.state.citely
    return state


def get_llm(request: Request) -> LLMProvider:
    return get_state(request).llm


def get_embedder(request: Request) -> EmbeddingProvider:
    return get_state(request).embedder


def resolve_llm(state: AppState, model: str | None) -> LLMProvider:
    """Return the LLM for a request, honoring an optional per-request model override.

    Overrides apply only to the Ollama provider (swapping a chat model is just a different
    string in the API call). For other providers — or when the requested model matches the
    configured default — the shared singleton is returned unchanged.
    """
    if not model or model == state.llm.model_name:
        return state.llm
    if state.cfg.provider is not LLMProviderKind.ollama:
        return state.llm
    cached = state.llm_cache.get(model)
    if cached is None:
        from citely.providers.ollama import OllamaProvider

        cached = OllamaProvider(
            model=model,
            host=state.cfg.providers.ollama_host,
            num_ctx=state.cfg.models.num_ctx,
            timeout_s=state.cfg.providers.request_timeout_s,
        )
        state.llm_cache[model] = cached
    return cached


def build_retriever(
    state: AppState, session: AsyncSession, llm: LLMProvider
) -> HybridRetriever:
    """Assemble a request-scoped HybridRetriever using the given (possibly overridden) LLM.

    The query constructor (metadata + translation) is rebuilt per request because it binds
    to ``llm``; the embedder, reranker and BM25 index remain shared singletons.
    """
    repository = PassageRepository(session)
    return HybridRetriever(
        state.cfg,
        build_query_constructor(llm, state.cfg),
        SparseRetriever(state.bm25_index),
        DenseRetriever(state.embedder, repository),
        state.reranker,
    )


def get_retriever(
    request: Request, session: AsyncSession = Depends(get_session)
) -> HybridRetriever:
    """Default retriever using the configured LLM (no per-request override)."""
    state = get_state(request)
    return build_retriever(state, session, state.llm)


def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    return session
