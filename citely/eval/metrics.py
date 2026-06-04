"""Eval metrics: recall_at_k, citation_accuracy, faithfulness.

``recall_at_k`` and ``citation_accuracy`` are pure and deterministic (covered by
tests/test_metrics.py). ``faithfulness`` summarizes verifier output. Empty-input
conventions are chosen so a metric never raises and reads sensibly: recall over no
relevant ids is 0.0, citation accuracy over zero citations is 1.0 (no dangling refs),
faithfulness over zero claims is 0.0 (nothing supported).
"""

from __future__ import annotations


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """Fraction of relevant ids present in the top-k retrieved ids."""
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    top_k = set(retrieved_ids[:k])
    return len(relevant & top_k) / len(relevant)


def citation_accuracy(claims: list[dict], valid_source_ids: set[str]) -> float:
    """Fraction of claim citations that point to a real, provided source id."""
    total = 0
    valid = 0
    for claim in claims:
        for sid in claim.get("source_ids", []):
            total += 1
            if sid in valid_source_ids:
                valid += 1
    if total == 0:
        return 1.0
    return valid / total


def faithfulness(claims: list[dict]) -> float:
    """Fraction of claims marked supported by the verifier."""
    if not claims:
        return 0.0
    supported = sum(1 for claim in claims if claim.get("supported") is True)
    return supported / len(claims)
