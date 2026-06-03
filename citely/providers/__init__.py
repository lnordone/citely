"""Providers: the spine. All model access flows through these interfaces.

Only base types and the factory builders are re-exported here. Concrete provider
modules are imported lazily by the factory to avoid pulling heavy/optional client
libraries unless the corresponding provider is selected.
"""

from citely.providers.base import (
    EmbeddingProvider,
    GenerationConfig,
    LLMProvider,
    Message,
    StructuredOutputError,
)
from citely.providers.factory import (
    build_embedding_provider,
    build_llm_provider,
    build_reranker,
)

__all__ = [
    "EmbeddingProvider",
    "GenerationConfig",
    "LLMProvider",
    "Message",
    "StructuredOutputError",
    "build_embedding_provider",
    "build_llm_provider",
    "build_reranker",
]
