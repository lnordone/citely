"""ClaimVerifier: entailment check per claim against its cited sources.

Uses LLMProvider.generate_json. Injected provider only.

# TODO(phase 7): for each claim, ask the model if the cited sources entail it; set
# Claim.supported.
"""

from __future__ import annotations

from citely.providers.base import LLMProvider
from citely.retrieval.types import Claim, RetrievedPassage


class ClaimVerifier:
    def __init__(self, llm: LLMProvider, enabled: bool = True) -> None:
        self._llm = llm
        self._enabled = enabled

    async def verify(
        self, claim: Claim, sources: list[RetrievedPassage]
    ) -> Claim:
        raise NotImplementedError  # TODO(phase 7)
