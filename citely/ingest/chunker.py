"""Abstract -> passages (token-based windows, overlap, parent link).

# TODO(phase 3): tokenize (tiktoken), window by chunk_tokens with chunk_overlap, assign
# deterministic ids and chunk_index, keep paper_id parent link.
"""

from __future__ import annotations

from dataclasses import dataclass


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
        self._chunk_tokens = chunk_tokens
        self._chunk_overlap = chunk_overlap

    def chunk(self, paper_id: str, text: str) -> list[Chunk]:
        """Split ``text`` into overlapping token windows linked to ``paper_id``."""
        raise NotImplementedError  # TODO(phase 3)
