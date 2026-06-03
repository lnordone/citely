"""QueryTranslator: none | multi_query | hyde | (decompose stub).

Produces the dense-leg query variants per ``config.query.translation.method``. Uses the
injected LLMProvider. The original query is always retained as the first variant so the
dense leg never loses the user's literal intent; translation is best-effort and degrades
to ``[query]`` on any failure.
"""

from __future__ import annotations

from citely.config import Config, TranslationMethod
from citely.logging import get_logger
from citely.providers.base import LLMProvider, Message

log = get_logger(__name__)

_MULTI_QUERY_SCHEMA = {
    "type": "object",
    "properties": {"queries": {"type": "array", "items": {"type": "string"}}},
}


class QueryTranslator:
    def __init__(self, llm: LLMProvider, cfg: Config) -> None:
        self._llm = llm
        self._cfg = cfg

    async def translate(self, query: str) -> list[str]:
        """Return dense-leg query variants per config.query.translation.method."""
        method = self._cfg.query.translation.method
        if method is TranslationMethod.multi_query:
            return await self._multi_query(query, self._cfg.query.translation.num_variants)
        if method is TranslationMethod.hyde:
            return await self._hyde(query)
        # `none` and the `decompose` stub both fall back to the literal query.
        if method is TranslationMethod.decompose:
            log.info("translate.decompose_stub")
        return [query]

    async def _multi_query(self, query: str, num_variants: int) -> list[str]:
        system = Message(
            "system",
            f"Rewrite the user's search query into {num_variants} diverse paraphrases that "
            "use different phrasings and synonyms to retrieve academic papers. Preserve the "
            "meaning. Respond with JSON: an object with a 'queries' array of strings.",
        )
        try:
            data = await self._llm.generate_json([system, Message("user", query)], _MULTI_QUERY_SCHEMA)
        except Exception as exc:
            log.warning("translate.multi_query_failed", error=str(exc))
            return [query]

        variants = [query]
        raw = data.get("queries")
        if isinstance(raw, list):
            for item in raw:
                candidate = item.strip() if isinstance(item, str) else ""
                if candidate and candidate not in variants:
                    variants.append(candidate)
        return variants[: num_variants + 1]

    async def _hyde(self, query: str) -> list[str]:
        system = Message(
            "system",
            "Write a short, factual paragraph (3-4 sentences) that reads like the abstract "
            "of a paper answering the user's question. Do not mention that you are an AI.",
        )
        try:
            doc = (await self._llm.generate([system, Message("user", query)])).strip()
        except Exception as exc:
            log.warning("translate.hyde_failed", error=str(exc))
            return [query]
        # Embed both the literal query and the hypothetical document.
        return [query, doc] if doc else [query]
