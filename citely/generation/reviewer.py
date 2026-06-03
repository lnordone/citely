"""ReviewGenerator.generate() -> streamed, cited review.

Uses LLMProvider.generate_json for the citation-grounded {text, source_ids} structure.
Injected provider only. Claims are yielded one at a time so the SSE path (phase 8) can
forward them as they are validated; each claim's citations are filtered to the actually
provided source ids, so a rendered review can never contain a dangling marker.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

from citely.config import Config
from citely.generation.prompts import REVIEW_SYSTEM_PROMPT, build_review_user_prompt
from citely.logging import get_logger
from citely.providers.base import GenerationConfig, LLMProvider, Message
from citely.retrieval.types import Claim, RetrievedPassage

log = get_logger(__name__)

_CLAIMS_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "source_ids"],
            },
        }
    },
}

_SID_RE = re.compile(r"\d+")


def _normalize_sid(raw: object) -> str | None:
    """Coerce model-emitted ids ('S1', '[S1]', '1') to the canonical 'S1' form."""
    if not isinstance(raw, str):
        return None
    match = _SID_RE.search(raw)
    return f"S{match.group()}" if match else None


def _source_dicts(sources: list[RetrievedPassage]) -> list[dict]:
    out: list[dict] = []
    for i, source in enumerate(sources, start=1):
        entry: dict = {"id": source.source_key or f"S{i}", "text": source.text}
        if source.paper is not None:
            entry["title"] = source.paper.title
            entry["year"] = source.paper.year
        out.append(entry)
    return out


class ReviewGenerator:
    def __init__(self, llm: LLMProvider, cfg: Config) -> None:
        self._llm = llm
        self._cfg = cfg

    async def generate(
        self, query: str, sources: list[RetrievedPassage]
    ) -> AsyncIterator[Claim]:
        """Yield grounded claims as they are produced."""
        if not sources:
            return

        source_dicts = _source_dicts(sources)
        valid_ids = {d["id"] for d in source_dicts}
        messages = [
            Message("system", REVIEW_SYSTEM_PROMPT),
            Message("user", build_review_user_prompt(query, source_dicts)),
        ]
        gen_cfg = GenerationConfig(
            temperature=self._cfg.generation.temperature,
            max_tokens=self._cfg.generation.max_tokens,
        )
        data = await self._llm.generate_json(messages, _CLAIMS_SCHEMA, gen_cfg)

        claims = data.get("claims")
        if not isinstance(claims, list):
            log.warning("review.no_claims")
            return

        for item in claims:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            ids = [
                norm
                for norm in (_normalize_sid(sid) for sid in item.get("source_ids", []))
                if norm is not None and norm in valid_ids
            ]
            if not ids:
                continue  # drop ungrounded claims
            yield Claim(text=text.strip(), source_ids=ids)
