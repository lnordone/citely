"""QueryConstructor: query -> ConstructedQuery (filters + legs).

Combines metadata extraction (filters) and translation (dense variants). The sparse
(BM25) leg always uses the literal query; the dense leg uses the translated variants.
"""

from __future__ import annotations

import asyncio

from citely.config import Config
from citely.providers.base import LLMProvider
from citely.query.metadata_extract import MetadataExtractor
from citely.query.translate import QueryTranslator
from citely.retrieval.types import ConstructedQuery


class QueryConstructor:
    def __init__(self, translator: QueryTranslator, extractor: MetadataExtractor) -> None:
        self._translator = translator
        self._extractor = extractor

    async def construct(self, query: str) -> ConstructedQuery:
        filters, dense_queries = await asyncio.gather(
            self._extractor.extract(query),
            self._translator.translate(query),
        )
        return ConstructedQuery(
            original=query,
            bm25_query=query,
            dense_queries=dense_queries or [query],
            filters=filters,
        )


def build_query_constructor(llm: LLMProvider, cfg: Config) -> QueryConstructor:
    """Wire a QueryConstructor from a shared LLM provider and config."""
    return QueryConstructor(
        translator=QueryTranslator(llm, cfg),
        extractor=MetadataExtractor(llm, enabled=cfg.query.extract_metadata),
    )
