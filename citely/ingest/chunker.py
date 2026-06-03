"""Abstract -> passages (token-based windows, overlap, parent link).

Tokenizes with tiktoken and slides a fixed-size window (``chunk_tokens``) with
``chunk_overlap`` tokens shared between neighbours. Ids are deterministic
(``{paper_id}::{chunk_index}``) so re-chunking the same paper upserts the same rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import tiktoken

# cl100k_base is a good general-purpose BPE; chunk sizes are token budgets, not exact
# model token counts, so the specific encoding is not load-bearing.
_ENCODING_NAME = "cl100k_base"


@lru_cache(maxsize=1)
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(_ENCODING_NAME)


@dataclass(frozen=True)
class Chunk:
    paper_id: str
    chunk_index: int
    text: str

    @property
    def id(self) -> str:
        return f"{self.paper_id}::{self.chunk_index}"


class Chunker:
    def __init__(self, chunk_tokens: int = 256, chunk_overlap: int = 32) -> None:
        if chunk_overlap >= chunk_tokens:
            raise ValueError("chunk_overlap must be smaller than chunk_tokens")
        self._chunk_tokens = chunk_tokens
        self._chunk_overlap = chunk_overlap
        self._stride = chunk_tokens - chunk_overlap

    def chunk(self, paper_id: str, text: str) -> list[Chunk]:
        """Split ``text`` into overlapping token windows linked to ``paper_id``."""
        enc = _encoding()
        tokens = enc.encode(text)
        if not tokens:
            return []

        chunks: list[Chunk] = []
        start = 0
        index = 0
        while start < len(tokens):
            window = tokens[start : start + self._chunk_tokens]
            chunk_text = enc.decode(window).strip()
            if chunk_text:
                chunks.append(Chunk(paper_id=paper_id, chunk_index=index, text=chunk_text))
                index += 1
            if start + self._chunk_tokens >= len(tokens):
                break
            start += self._stride
        return chunks
