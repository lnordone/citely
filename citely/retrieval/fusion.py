"""Reciprocal rank fusion.

# TODO(phase 5): implement RRF: score(d) = sum_l 1 / (k_rrf + rank_l(d)); return fused
# ranking. Pure and deterministic (covered by tests/test_fusion.py).
"""

from __future__ import annotations

from citely.retrieval.types import RetrievedPassage


def reciprocal_rank_fusion(
    lists: list[list[RetrievedPassage]], k_rrf: int = 60
) -> list[RetrievedPassage]:
    """Fuse multiple ranked lists into one via RRF; returns fused ranking."""
    raise NotImplementedError  # TODO(phase 5)
