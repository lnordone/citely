"""RRF math on known inputs — pure, deterministic. (phase 5)"""

from __future__ import annotations

import pytest

from citely.retrieval.fusion import reciprocal_rank_fusion
from citely.retrieval.types import RetrievedPassage

pytestmark = pytest.mark.skip(reason="TODO(phase 5): implement reciprocal_rank_fusion")


def _p(pid: str) -> RetrievedPassage:
    return RetrievedPassage(passage_id=pid, paper_id=pid, text=pid, score=0.0)


def test_rrf_rewards_agreement_across_lists() -> None:
    list_a = [_p("x"), _p("y"), _p("z")]
    list_b = [_p("y"), _p("x"), _p("w")]
    fused = reciprocal_rank_fusion([list_a, list_b], k_rrf=60)
    # "y" and "x" appear high in both lists; they should top the fusion.
    assert {fused[0].passage_id, fused[1].passage_id} == {"x", "y"}
