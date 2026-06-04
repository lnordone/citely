"""recall_at_k / citation_accuracy / faithfulness on toy data. (phase 9)"""

from __future__ import annotations

import pytest

from citely.eval.metrics import citation_accuracy, faithfulness, recall_at_k


def test_recall_at_k() -> None:
    assert recall_at_k(["a", "b", "c"], ["a", "z"], k=3) == pytest.approx(0.5)


def test_recall_at_k_respects_cutoff() -> None:
    # "a" is relevant but falls outside the top-2 window.
    assert recall_at_k(["x", "y", "a"], ["a"], k=2) == pytest.approx(0.0)


def test_recall_at_k_no_relevant_is_zero() -> None:
    assert recall_at_k(["a", "b"], [], k=2) == pytest.approx(0.0)


def test_citation_accuracy() -> None:
    claims = [{"source_ids": ["S1", "S9"]}, {"source_ids": ["S2"]}]
    assert citation_accuracy(claims, {"S1", "S2"}) == pytest.approx(2 / 3)


def test_citation_accuracy_no_citations_is_perfect() -> None:
    assert citation_accuracy([{"source_ids": []}], {"S1"}) == pytest.approx(1.0)


def test_faithfulness() -> None:
    claims = [{"supported": True}, {"supported": False}, {"supported": True}]
    assert faithfulness(claims) == pytest.approx(2 / 3)


def test_faithfulness_empty_is_zero() -> None:
    assert faithfulness([]) == pytest.approx(0.0)
