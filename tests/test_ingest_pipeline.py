"""stream_ingest control flow: scan-from-newest, skip-already-stored, stop at max_papers.

The DB and arXiv are both faked. What's under test is the decision logic: which records
get chunked and written, what the counters say, and when the scan stops.
"""

from __future__ import annotations

import pytest

from citely.config import Config
from citely.ingest import pipeline as pipeline_mod
from citely.ingest.chunker import Chunker
from citely.ingest.pipeline import run_ingest, stream_ingest


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def commit(self) -> None:
        self.commits += 1


class FakePaperRepo:
    """Mimics ``INSERT ... ON CONFLICT DO NOTHING``: True only on first sight of an id."""

    def __init__(self, stored: set[str]) -> None:
        self.stored = stored

    async def upsert(self, paper: object) -> bool:
        pid = paper.id  # type: ignore[attr-defined]
        if pid in self.stored:
            return False
        self.stored.add(pid)
        return True


class FakePassageRepo:
    def __init__(self) -> None:
        self.rows: list[object] = []

    async def bulk_upsert(self, rows: list[object]) -> None:
        self.rows.extend(rows)

    async def count_embedded(self) -> int:
        return 0


class CountingChunker(Chunker):
    """Real chunker that records how many abstracts it was asked to tokenize."""

    calls = 0

    def chunk(self, paper_id: str, text: str):  # type: ignore[no-untyped-def]
        CountingChunker.calls += 1
        return super().chunk(paper_id, text)


def _record(n: int) -> dict:
    return {
        "id": f"http://arxiv.org/abs/2401.{n:05d}v1",
        "title": f"Paper {n}",
        "summary": f"Abstract number {n}. " * 5,
        "authors": ["A"],
        "categories": ["cs.LG"],
        "published": "2024-01-02T00:00:00Z",
        "pdf_url": "",
    }


@pytest.fixture
def harness(monkeypatch):
    """Patch the pipeline's DB + arXiv seams; return handles to the fakes."""
    state: dict = {"stored": set(), "passages": FakePassageRepo(), "yielded": []}
    CountingChunker.calls = 0

    monkeypatch.setattr(pipeline_mod, "init_db", lambda cfg: lambda: FakeSession())
    monkeypatch.setattr(pipeline_mod, "PaperRepository", lambda s: FakePaperRepo(state["stored"]))
    monkeypatch.setattr(pipeline_mod, "PassageRepository", lambda s: state["passages"])
    monkeypatch.setattr(pipeline_mod, "Chunker", CountingChunker)

    def set_feed(records: list[dict]) -> None:
        class FakeClient:
            def __init__(self, **_kw: object) -> None:
                pass

            async def search(self, _categories, _max_results):
                for r in records:
                    state["yielded"].append(r["id"])
                    yield r

        monkeypatch.setattr(pipeline_mod, "ArxivClient", FakeClient)

    state["set_feed"] = set_feed
    return state


async def _run(cfg: Config, **kw) -> list[dict]:
    return [e async for e in stream_ingest(cfg, ["cs.LG"], **kw)]


async def test_stores_new_papers_and_counts_them(harness):
    harness["set_feed"]([_record(i) for i in range(5)])
    events = await _run(Config(), max_papers=10)

    done = events[-1]
    assert done["phase"] == "done"
    assert done["papers_stored"] == 5
    assert done["papers_scanned"] == 5
    assert done["passages_stored"] == len(harness["passages"].rows)


async def test_already_stored_papers_are_skipped_without_chunking(harness):
    """The resume path: a second run over the same feed must write nothing new.

    Chunking is a tiktoken encode per abstract, so skipping it is what makes walking
    past an existing corpus cheap.
    """
    harness["set_feed"]([_record(i) for i in range(5)])
    await _run(Config(), max_papers=10)
    chunk_calls_first_run = CountingChunker.calls
    passages_after_first = len(harness["passages"].rows)
    assert chunk_calls_first_run == 5

    events = await _run(Config(), max_papers=10)

    done = events[-1]
    assert done["papers_stored"] == 0
    assert done["papers_scanned"] == 5  # every record was still examined
    assert CountingChunker.calls == chunk_calls_first_run  # no re-chunking
    assert len(harness["passages"].rows) == passages_after_first  # no re-write


async def test_scan_walks_past_stored_papers_to_reach_new_ones(harness):
    """Papers 0-4 are already stored; the new ones sit behind them in the feed."""
    harness["set_feed"]([_record(i) for i in range(5)])
    await _run(Config(), max_papers=10)

    harness["set_feed"]([_record(i) for i in range(8)])
    events = await _run(Config(), max_papers=10)

    done = events[-1]
    assert done["papers_scanned"] == 8
    assert done["papers_stored"] == 3


async def test_stops_once_max_papers_new_ones_are_stored(harness):
    harness["set_feed"]([_record(i) for i in range(100)])
    events = await _run(Config(), max_papers=3)

    done = events[-1]
    assert done["papers_stored"] == 3
    # The scan must stop at the target, not drain the whole feed.
    assert done["papers_scanned"] == 3
    assert len(harness["yielded"]) == 3


async def test_max_papers_counts_new_papers_not_records_seen(harness):
    """With 2 of 5 already stored, asking for 3 new must still yield 3 new."""
    harness["set_feed"]([_record(i) for i in range(2)])
    await _run(Config(), max_papers=10)

    harness["set_feed"]([_record(i) for i in range(10)])
    events = await _run(Config(), max_papers=3)

    done = events[-1]
    assert done["papers_stored"] == 3
    assert done["papers_scanned"] == 5  # 2 skipped + 3 stored


async def test_malformed_records_are_skipped_but_counted_as_scanned(harness):
    bad = _record(1)
    bad["published"] = ""
    harness["set_feed"]([_record(0), bad, _record(2)])

    events = await _run(Config(), max_papers=10)

    done = events[-1]
    assert done["papers_stored"] == 2
    assert done["papers_scanned"] == 3


async def test_progress_events_expose_the_scan_counter(harness):
    harness["set_feed"]([_record(i) for i in range(3)])
    events = await _run(Config(), max_papers=10)

    fetch = [e for e in events if e["phase"] == "fetch"]
    assert [e["scanned"] for e in fetch] == [1, 2, 3]
    assert [e["papers"] for e in fetch] == [1, 2, 3]
    assert all(e["max_papers"] == 10 for e in fetch)


async def test_run_ingest_wrapper_mirrors_the_done_event(harness):
    harness["set_feed"]([_record(i) for i in range(4)])
    stats = await run_ingest(Config(), ["cs.LG"], max_papers=10)

    assert stats.papers_scanned == 4
    assert stats.papers_stored == 4
    assert stats.passages_stored == len(harness["passages"].rows)
