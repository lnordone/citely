"""recall_at_k / citation_accuracy on toy data. (phase 9)"""

from __future__ import annotations

import pytest

from citely.eval.metrics import citation_accuracy, recall_at_k

pytestmark = pytest.mark.skip(reason="TODO(phase 9): implement metrics")


def test_recall_at_k() -> None:
    assert recall_at_k(["a", "b", "c"], ["a", "z"], k=3) == pytest.approx(0.5)


def test_citation_accuracy() -> None:
    claims = [{"source_ids": ["S1", "S9"]}, {"source_ids": ["S2"]}]
    assert citation_accuracy(claims, {"S1", "S2"}) == pytest.approx(2 / 3)
