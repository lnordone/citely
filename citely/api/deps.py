"""Dependency providers: get_db, get_llm, get_embedder, get_retriever, ...

Providers are built once (via the factory) at app startup and handed out here; routes
never instantiate clients directly.

# TODO(phase 8): wire these to app.state populated in the lifespan.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citely.providers.base import EmbeddingProvider, LLMProvider


def get_llm() -> LLMProvider:
    raise NotImplementedError  # TODO(phase 8)


def get_embedder() -> EmbeddingProvider:
    raise NotImplementedError  # TODO(phase 8)


def get_retriever() -> object:
    raise NotImplementedError  # TODO(phase 8)


def get_db() -> object:
    raise NotImplementedError  # TODO(phase 8)
