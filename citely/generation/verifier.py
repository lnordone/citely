"""ClaimVerifier: entailment check per claim against its cited sources.

Uses LLMProvider.generate_json. Injected provider only. Verification is a guardrail, not
a hard gate: when disabled it is a no-op, and on any LLM/parse failure the claim's
``supported`` is left as ``None`` (unknown) rather than dropping the claim.
"""

from __future__ import annotations

from citely.generation.prompts import VERIFIER_SYSTEM_PROMPT, build_verifier_user_prompt
from citely.logging import get_logger
from citely.providers.base import LLMProvider, Message
from citely.retrieval.types import Claim, RetrievedPassage

log = get_logger(__name__)

_VERIFY_SCHEMA = {
    "type": "object",
    "properties": {"supported": {"type": "boolean"}},
    "required": ["supported"],
}


class ClaimVerifier:
    def __init__(self, llm: LLMProvider, enabled: bool = True) -> None:
        self._llm = llm
        self._enabled = enabled

    async def verify(self, claim: Claim, sources: list[RetrievedPassage]) -> Claim:
        if not self._enabled:
            return claim

        cited = [s for s in sources if s.source_key and s.source_key in claim.source_ids]
        if not cited:
            cited = sources
        source_dicts = [{"id": s.source_key, "text": s.text} for s in cited]
        messages = [
            Message("system", VERIFIER_SYSTEM_PROMPT),
            Message("user", build_verifier_user_prompt(claim.text, source_dicts)),
        ]
        try:
            data = await self._llm.generate_json(messages, _VERIFY_SCHEMA)
        except Exception as exc:  # best-effort: verification must never be fatal
            log.warning("verify.failed", error=str(exc))
            claim.supported = None
            return claim

        supported = data.get("supported")
        claim.supported = supported if isinstance(supported, bool) else None
        return claim
