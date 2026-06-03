"""Extract date/category/author filters from the query (rules + LLM self-query).

Rules run first (cheap, deterministic regex for years and arXiv category codes); the
LLM ``generate_json`` self-query path only runs as a fallback when the rules find
nothing. Extraction is best-effort — any failure degrades to "no filters" rather than
breaking retrieval.
"""

from __future__ import annotations

import re
from datetime import date

from citely.logging import get_logger
from citely.providers.base import LLMProvider, Message
from citely.retrieval.types import QueryFilters

log = get_logger(__name__)

# 1990-2099; the only temporal filter we support is a lower bound (date_after).
_YEAR_RE = re.compile(r"\b(19[9]\d|20\d\d)\b")
# arXiv category codes, e.g. cs.AI, cs.LG, eess.SP, math.CO, cond-mat.stat-mech head.
_CATEGORY_RE = re.compile(r"\b([a-z]{2,}(?:-[a-z]+)?\.[A-Za-z]{2,})\b")

_FILTER_SCHEMA = {
    "type": "object",
    "properties": {
        "date_after": {
            "type": ["string", "null"],
            "description": "lower-bound publication date as YYYY-MM-DD, or null",
        },
        "categories": {
            "type": "array",
            "items": {"type": "string"},
            "description": "arXiv category codes mentioned, e.g. cs.AI",
        },
        "authors": {"type": "array", "items": {"type": "string"}},
    },
}

_SYSTEM = Message(
    "system",
    "You extract structured retrieval filters from a user's query about arXiv papers. "
    "Only include a field when the query clearly implies it; otherwise use null / an "
    "empty list. Never invent authors or categories. Respond with JSON only.",
)


class MetadataExtractor:
    def __init__(self, llm: LLMProvider, enabled: bool = True) -> None:
        self._llm = llm
        self._enabled = enabled

    async def extract(self, query: str) -> QueryFilters:
        rules = self._rule_based(query)
        if not self._enabled or not rules.is_empty():
            return rules
        return await self._llm_based(query)

    def _rule_based(self, query: str) -> QueryFilters:
        filters = QueryFilters()
        year = _YEAR_RE.search(query)
        if year:
            filters.date_after = date(int(year.group(1)), 1, 1)
        categories = _CATEGORY_RE.findall(query)
        if categories:
            filters.categories = categories
        return filters

    async def _llm_based(self, query: str) -> QueryFilters:
        try:
            data = await self._llm.generate_json([_SYSTEM, Message("user", query)], _FILTER_SCHEMA)
        except Exception as exc:
            log.warning("metadata.extract_failed", error=str(exc))
            return QueryFilters()
        return self._parse(data)

    def _parse(self, data: dict) -> QueryFilters:
        filters = QueryFilters()
        raw_date = data.get("date_after")
        if isinstance(raw_date, str) and raw_date.strip():
            filters.date_after = self._parse_date(raw_date.strip())
        categories = self._clean_list(data.get("categories"))
        if categories:
            filters.categories = categories
        authors = self._clean_list(data.get("authors"))
        if authors:
            filters.authors = authors
        return filters

    @staticmethod
    def _clean_list(value: object) -> list[str] | None:
        if not isinstance(value, list):
            return None
        cleaned = [v.strip() for v in value if isinstance(v, str) and v.strip()]
        return cleaned or None

    @staticmethod
    def _parse_date(value: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except ValueError:
            match = _YEAR_RE.search(value)
            return date(int(match.group(1)), 1, 1) if match else None
