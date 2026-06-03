"""ReviewGenerator.generate() -> streamed, cited review.

Uses LLMProvider.generate_json for the citation-grounded {text, source_ids} structure
and LLMProvider.stream for the SSE path. Injected provider only.

# TODO(phase 7): build the prompt from retrieved sources, stream claims with citations.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from citely.config import Config
from citely.providers.base import LLMProvider
from citely.retrieval.types import Claim, RetrievedPassage


class ReviewGenerator:
    def __init__(self, llm: LLMProvider, cfg: Config) -> None:
        self._llm = llm
        self._cfg = cfg

    async def generate(
        self, query: str, sources: list[RetrievedPassage]
    ) -> AsyncIterator[Claim]:
        """Yield grounded claims as they are produced."""
        raise NotImplementedError  # TODO(phase 7)
        yield  # pragma: no cover - keeps this a valid async generator
