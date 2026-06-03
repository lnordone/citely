"""RRF math on known inputs — pure, deterministic. (phase 5)"""

from __future__ import annotations

from citely.retrieval.fusion import reciprocal_rank_fusion
from citely.retrieval.types import RetrievedPassage


def _p(pid: str) -> RetrievedPassage:
    return RetrievedPassage(passage_id=pid, paper_id=pid, text=pid, score=0.0)


def test_rrf_rewards_agreement_across_lists() -> None:
    list_a = [_p("x"), _p("y"), _p("z")]
    list_b = [_p("y"), _p("x"), _p("w")]
    fused = reciprocal_rank_fusion([list_a, list_b], k_rrf=60)
    # "y" and "x" appear high in both lists; they should top the fusion.
    assert {fused[0].passage_id, fused[1].passage_id} == {"x", "y"}
    # Every unique id appears exactly once in the fused output.
    assert sorted(p.passage_id for p in fused) == ["w", "x", "y", "z"]


def test_rrf_single_list_preserves_order() -> None:
    fused = reciprocal_rank_fusion([[_p("a"), _p("b"), _p("c")]], k_rrf=60)
    assert [p.passage_id for p in fused] == ["a", "b", "c"]
    # Scores are strictly decreasing with rank.
    assert fused[0].score > fused[1].score > fused[2].score


def test_rrf_higher_rank_outweighs_when_tie_broken_by_id() -> None:
    # Disjoint lists -> ties at equal ranks resolve deterministically by passage_id.
    fused = reciprocal_rank_fusion([[_p("b")], [_p("a")]], k_rrf=60)
    assert [p.passage_id for p in fused] == ["a", "b"]


def test_rrf_empty() -> None:
    assert reciprocal_rank_fusion([], k_rrf=60) == []
    assert reciprocal_rank_fusion([[], []], k_rrf=60) == []
