"""QueryConstructor: query -> ConstructedQuery (filters + legs).

Combines metadata extraction (filters) and translation (dense variants).

# TODO(phase 6): assemble bm25_query, dense_queries, and filters into ConstructedQuery.
"""

from __future__ import annotations

from citely.query.metadata_extract import MetadataExtractor
from citely.query.translate import QueryTranslator
from citely.retrieval.types import ConstructedQuery


class QueryConstructor:
    def __init__(self, translator: QueryTranslator, extractor: MetadataExtractor) -> None:
        self._translator = translator
        self._extractor = extractor

    async def construct(self, query: str) -> ConstructedQuery:
        raise NotImplementedError  # TODO(phase 6)
