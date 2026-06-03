"""Extract date/category filters from the query (LLM structured output + rules).

Uses the injected LLMProvider.generate_json — no direct client.

# TODO(phase 6): rules first (regex for years/categories), then LLM self-query fallback.
"""

from __future__ import annotations

from citely.providers.base import LLMProvider
from citely.retrieval.types import QueryFilters


class MetadataExtractor:
    def __init__(self, llm: LLMProvider, enabled: bool = True) -> None:
        self._llm = llm
        self._enabled = enabled

    async def extract(self, query: str) -> QueryFilters:
        raise NotImplementedError  # TODO(phase 6)
