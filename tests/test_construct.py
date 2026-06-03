"""Filter extraction incl. the no-filter case, plus translation/construction. (phase 6)"""

from __future__ import annotations

from datetime import date

from citely.config import Config
from citely.query.construct import QueryConstructor, build_query_constructor
from citely.query.metadata_extract import MetadataExtractor
from citely.query.translate import QueryTranslator


async def test_no_filter_case(mock_llm) -> None:
    filters = await MetadataExtractor(mock_llm).extract("survey of attention mechanisms")
    assert filters.is_empty()


async def test_extracts_year(mock_llm) -> None:
    filters = await MetadataExtractor(mock_llm).extract("papers since 2022 on RAG")
    assert filters.date_after == date(2022, 1, 1)


async def test_extracts_category_code(mock_llm) -> None:
    filters = await MetadataExtractor(mock_llm).extract("recent cs.LG work on dropout")
    assert filters.categories == ["cs.LG"]


async def test_disabled_extractor_skips_llm(mock_llm) -> None:
    extractor = MetadataExtractor(mock_llm, enabled=False)
    filters = await extractor.extract("survey of attention mechanisms")
    assert filters.is_empty()
    assert mock_llm.calls == []  # no LLM fallback when disabled


async def test_translate_retains_original(mock_llm) -> None:
    # The mock returns no 'queries', so translation degrades to the literal query.
    variants = await QueryTranslator(mock_llm, Config()).translate("graph neural networks")
    assert variants[0] == "graph neural networks"


async def test_construct_assembles_query(mock_llm) -> None:
    constructor: QueryConstructor = build_query_constructor(mock_llm, Config())
    cq = await constructor.construct("papers since 2022 on cs.CL retrieval")
    assert cq.original == "papers since 2022 on cs.CL retrieval"
    assert cq.bm25_query == "papers since 2022 on cs.CL retrieval"
    assert cq.dense_queries[0] == "papers since 2022 on cs.CL retrieval"
    assert cq.filters.date_after == date(2022, 1, 1)
    assert cq.filters.categories == ["cs.CL"]
