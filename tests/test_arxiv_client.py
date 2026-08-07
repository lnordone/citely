"""ArxivClient query building, record projection, and the paging loop.

``_fetch_page`` is stubbed throughout — these tests never touch the network.
"""

from __future__ import annotations

import pytest

from citely.ingest.arxiv_client import (
    MAX_OFFSET,
    ArxivClient,
    _build_search_query,
    _entry_to_record,
)


def test_categories_are_ored_with_the_cat_prefix():
    assert _build_search_query(["cs.AI"]) == "cat:cs.AI"
    assert _build_search_query(["cs.*", "eess.*"]) == "cat:cs.* OR cat:eess.*"


def test_empty_category_list_is_rejected():
    with pytest.raises(ValueError):
        _build_search_query([])


def test_entry_projection_picks_the_pdf_link():
    entry = {
        "id": "http://arxiv.org/abs/2401.1v1",
        "title": "T",
        "summary": "S",
        "authors": [{"name": "A"}],
        "tags": [{"term": "cs.LG"}],
        "published": "2024-01-02T00:00:00Z",
        "links": [
            {"href": "http://arxiv.org/abs/2401.1v1", "type": "text/html"},
            {"href": "http://arxiv.org/pdf/2401.1v1", "type": "application/pdf"},
        ],
    }
    record = _entry_to_record(entry)
    assert record["pdf_url"] == "http://arxiv.org/pdf/2401.1v1"
    assert record["authors"] == ["A"]
    assert record["categories"] == ["cs.LG"]


def _client_with_pages(monkeypatch, pages: list[list[dict]]) -> tuple[ArxivClient, list[int]]:
    """Client whose ``_fetch_page`` serves canned pages; records requested offsets."""
    client = ArxivClient(min_interval_s=0.0)
    offsets: list[int] = []
    calls = {"n": 0}

    async def fake_fetch_page(_self, _http, _query, start, _count):
        offsets.append(start)
        i = calls["n"]
        calls["n"] += 1
        return pages[i] if i < len(pages) else []

    monkeypatch.setattr(ArxivClient, "_fetch_page", fake_fetch_page)
    return client, offsets


def _entries(n: int, base: int = 0) -> list[dict]:
    return [{"id": f"http://arxiv.org/abs/24.{base + i}", "links": []} for i in range(n)]


async def test_search_stops_at_max_results_mid_page(monkeypatch):
    client, _ = _client_with_pages(monkeypatch, [_entries(100)])
    got = [r async for r in client.search(["cs.AI"], 5)]
    assert len(got) == 5


async def test_search_pages_forward_until_exhausted(monkeypatch):
    client, offsets = _client_with_pages(
        monkeypatch, [_entries(100), _entries(40, base=100), []]
    )
    got = [r async for r in client.search(["cs.AI"], 1000)]
    assert len(got) == 140
    # Second page must resume after the first, not re-request offset 0.
    assert offsets[:2] == [0, 100]


async def test_search_stops_at_the_atom_offset_ceiling(monkeypatch):
    # The API refuses to page past MAX_OFFSET; the client must not spin forever asking.
    client, offsets = _client_with_pages(monkeypatch, [_entries(100)] * 1000)
    got = [r async for r in client.search(["cs.AI"], 10**9)]
    assert len(got) == MAX_OFFSET
    assert max(offsets) < MAX_OFFSET


async def test_empty_first_page_ends_the_scan(monkeypatch):
    client, _ = _client_with_pages(monkeypatch, [[]])
    assert [r async for r in client.search(["cs.AI"], 100)] == []
