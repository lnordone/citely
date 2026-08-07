"""Provider factory: the ONLY place provider classes are instantiated.

Everything else receives a provider via dependency injection. Provider submodules are
imported lazily inside each builder so that selecting (say) Ollama never imports the
``openai``/``anthropic``/``sentence_transformers`` stacks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from citely.config import (
    Config,
    EmbeddingProviderKind,
    LLMProviderKind,
)
from citely.providers.base import EmbeddingProvider, LLMProvider

if TYPE_CHECKING:
    from citely.retrieval.rerank import Reranker


def build_llm_provider(cfg: Config, model: str | None = None) -> LLMProvider:
    """Switch on ``cfg.provider``.

    ``model`` overrides the configured model name for the active provider (used by the
    per-request model override on ``/search`` and ``/review``); ``None`` keeps the
    configured default. The provider itself is never switched per request — only the
    model it asks for.
    """
    kind = cfg.provider
    if kind is LLMProviderKind.ollama:
        from citely.providers.ollama import build_ollama_llm

        return build_ollama_llm(cfg, model)
    if kind is LLMProviderKind.openai:
        from citely.providers.openai import build_openai_llm

        return build_openai_llm(cfg, model)
    if kind is LLMProviderKind.anthropic:
        from citely.providers.anthropic import build_anthropic_llm

        return build_anthropic_llm(cfg, model)
    raise ValueError(f"unknown LLM provider: {kind!r}")


def build_embedding_provider(cfg: Config) -> EmbeddingProvider:
    """Switch on ``cfg.embedding_provider``."""
    kind = cfg.embedding_provider
    if kind is EmbeddingProviderKind.local:
        from citely.providers.local import build_local_embedding

        return build_local_embedding(cfg)
    if kind is EmbeddingProviderKind.ollama:
        from citely.providers.ollama import build_ollama_embedding

        return build_ollama_embedding(cfg)
    if kind is EmbeddingProviderKind.openai:
        from citely.providers.openai import build_openai_embedding

        return build_openai_embedding(cfg)
    raise ValueError(f"unknown embedding provider: {kind!r}")


def build_reranker(cfg: Config) -> Reranker:
    """Build the cross-encoder reranker (default: BAAI/bge-reranker-base).

    Imported lazily; the concrete ``Reranker`` interface and implementation live in
    ``citely.retrieval.rerank`` (phase 5).
    """
    from citely.retrieval.rerank import CrossEncoderReranker

    return CrossEncoderReranker(model=cfg.models.reranker, final_k=cfg.retrieval.final_k)
