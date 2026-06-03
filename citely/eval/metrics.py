"""Eval metrics: recall_at_k, citation_accuracy, faithfulness.

# TODO(phase 9): implement metrics. recall_at_k and citation_accuracy are pure and
# deterministic (covered by tests/test_metrics.py).
"""

from __future__ import annotations


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """Fraction of relevant ids present in the top-k retrieved ids."""
    raise NotImplementedError  # TODO(phase 9)


def citation_accuracy(claims: list[dict], valid_source_ids: set[str]) -> float:
    """Fraction of claim citations that point to a real, provided source id."""
    raise NotImplementedError  # TODO(phase 9)


def faithfulness(claims: list[dict]) -> float:
    """Fraction of claims marked supported by the verifier."""
    raise NotImplementedError  # TODO(phase 9)
