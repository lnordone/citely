"""Citation markers map to real sources. (phase 7)"""

from __future__ import annotations

from citely.generation.render import render_markdown
from citely.retrieval.types import Claim, PaperRef, RetrievedPassage


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


def test_dangling_citation_is_dropped() -> None:
    sources = [_source("S1")]
    claims = [Claim(text="Mixed cites.", source_ids=["S1", "S9"])]
    md = render_markdown(claims, sources)
    assert "[S1]" in md
    assert "[S9]" not in md


def test_bibliography_lists_only_cited_sources() -> None:
    sources = [_source("S1"), _source("S2")]
    claims = [Claim(text="A finding.", source_ids=["S2"])]
    md = render_markdown(claims, sources)
    assert "## Sources" in md
    assert "**[S2]**" in md
    assert "**[S1]**" not in md  # S1 was never cited


def test_unverified_claim_is_flagged() -> None:
    sources = [_source("S1")]
    claims = [Claim(text="Shaky claim.", source_ids=["S1"], supported=False)]
    md = render_markdown(claims, sources)
    assert "*(unverified)*" in md


def test_no_claims_renders_placeholder() -> None:
    assert "No grounded claims" in render_markdown([], [_source("S1")])
