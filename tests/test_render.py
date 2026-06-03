"""Citation markers map to real sources. (phase 7)"""

from __future__ import annotations

import pytest

from citely.generation.render import render_markdown
from citely.retrieval.types import Claim, PaperRef, RetrievedPassage

pytestmark = pytest.mark.skip(reason="TODO(phase 7): implement render_markdown")


def _source(key: str) -> RetrievedPassage:
    return RetrievedPassage(
        passage_id=f"{key}-p",
        paper_id=f"{key}-paper",
        text="some passage text",
        score=1.0,
        source_key=key,
        paper=PaperRef(f"{key}-paper", "A Title", ["Author"], 2023, "http://example.com"),
    )


def test_markers_reference_real_sources() -> None:
    sources = [_source("S1"), _source("S2")]
    claims = [Claim(text="A finding.", source_ids=["S1"])]
    md = render_markdown(claims, sources)
    assert "[S1]" in md
    assert "[S3]" not in md  # no dangling citations
