"""Reciprocal rank fusion.

# TODO(phase 5): implement RRF: score(d) = sum_l 1 / (k_rrf + rank_l(d)); return fused
# ranking. Pure and deterministic (covered by tests/test_fusion.py).
"""

from __future__ import annotations

from citely.retrieval.types import RetrievedPassage


def reciprocal_rank_fusion(
    lists: list[list[RetrievedPassage]], k_rrf: int = 60
) -> list[RetrievedPassage]:
    """Fuse ranked lists via RRF: score(d) = sum_l 1 / (k_rrf + rank_l(d)).

    Pure and deterministic. ``rank`` is 1-based. When the same passage appears in
    multiple lists, a representative object is kept (preferring one with hydrated text);
    its ``score`` is overwritten with the fused score. Ties break on ``passage_id``.
    """
    scores: dict[str, float] = {}
    rep: dict[str, RetrievedPassage] = {}
    for ranked in lists:
        for rank, passage in enumerate(ranked, start=1):
            pid = passage.passage_id
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (k_rrf + rank)
            current = rep.get(pid)
            if current is None or (not current.text and passage.text):
                rep[pid] = passage

    fused = list(rep.values())
    for passage in fused:
        passage.score = scores[passage.passage_id]
    fused.sort(key=lambda p: (-p.score, p.passage_id))
    return fused
