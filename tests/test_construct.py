"""Filter extraction incl. the no-filter case. (phase 6)"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="TODO(phase 6): implement MetadataExtractor.extract")


async def test_no_filter_case(mock_llm) -> None:  # noqa: ANN001
    from citely.query.metadata_extract import MetadataExtractor

    filters = await MetadataExtractor(mock_llm).extract("survey of attention mechanisms")
    assert filters.is_empty()


async def test_extracts_year(mock_llm) -> None:  # noqa: ANN001
    from citely.query.metadata_extract import MetadataExtractor

    filters = await MetadataExtractor(mock_llm).extract("papers since 2022 on RAG")
    assert filters.date_after is not None
