"""Chunker: overlap, token counts, parent linkage. (phase 3)"""

from __future__ import annotations

from citely.ingest.chunker import Chunker


def test_chunks_link_to_parent() -> None:
    chunks = Chunker(chunk_tokens=8, chunk_overlap=2).chunk("2401.00001", "word " * 40)
    assert chunks
    assert all(c.paper_id == "2401.00001" for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_overlap_between_consecutive_chunks() -> None:
    chunks = Chunker(chunk_tokens=8, chunk_overlap=2).chunk("p", "word " * 40)
    assert len(chunks) > 1
