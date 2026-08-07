"""normalize_record: raw arXiv entry -> Paper. Pure, no network."""

from __future__ import annotations

from datetime import date

import pytest

from citely.ingest.normalize import normalize_record


def _record(**overrides: object) -> dict:
    base = {
        "id": "http://arxiv.org/abs/2401.00001v2",
        "title": "A Title",
        "summary": "An abstract.",
        "authors": ["Ada Lovelace"],
        "categories": ["cs.LG"],
        "published": "2024-01-02T18:00:00Z",
        "pdf_url": "http://arxiv.org/pdf/2401.00001v2",
    }
    base.update(overrides)
    return base


def test_version_suffix_is_stripped_so_reingest_dedups():
    # The id is the dedup key: v1 and v2 of a paper must collapse onto one row.
    assert normalize_record(_record()).id == "2401.00001"
    v5 = _record(id="http://arxiv.org/abs/2401.00001v5")
    assert normalize_record(v5).id == "2401.00001"


def test_old_style_ids_keep_their_archive_prefix():
    paper = normalize_record(_record(id="http://arxiv.org/abs/cs/0501001v1"))
    assert paper.id == "cs/0501001"


def test_wrapped_whitespace_is_collapsed():
    paper = normalize_record(_record(title="A\n  wrapped   title", summary="Two\nlines."))
    assert paper.title == "A wrapped title"
    assert paper.abstract == "Two lines."


def test_published_is_parsed_to_a_date():
    assert normalize_record(_record()).published == date(2024, 1, 2)


def test_offset_timestamps_parse():
    paper = normalize_record(_record(published="2024-01-02T18:00:00+02:00"))
    assert paper.published == date(2024, 1, 2)


def test_missing_published_is_rejected():
    with pytest.raises(ValueError):
        normalize_record(_record(published=""))


def test_unparseable_id_is_rejected():
    with pytest.raises(ValueError):
        normalize_record(_record(id=""))


def test_empty_authors_and_categories_are_dropped():
    paper = normalize_record(_record(authors=["A", ""], categories=["cs.LG", ""]))
    assert paper.authors == ["A"]
    assert paper.categories == ["cs.LG"]


def test_pdf_url_falls_back_to_the_canonical_arxiv_path():
    paper = normalize_record(_record(pdf_url=""))
    assert paper.pdf_url == "https://arxiv.org/pdf/2401.00001"
