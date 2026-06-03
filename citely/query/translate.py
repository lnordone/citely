"""QueryTranslator: none | multi_query | hyde | (decompose stub).

Produces the dense-leg query variants. Uses the injected LLMProvider.

# TODO(phase 6): multi_query (N paraphrases), hyde (hypothetical doc), decompose (stub).
"""

from __future__ import annotations

from citely.config import Config
from citely.providers.base import LLMProvider


class QueryTranslator:
    def __init__(self, llm: LLMProvider, cfg: Config) -> None:
        self._llm = llm
        self._cfg = cfg

    async def translate(self, query: str) -> list[str]:
        """Return dense-leg query variants per config.query.translation.method."""
        raise NotImplementedError  # TODO(phase 6)
