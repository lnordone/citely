"""Prompt templates for the reviewer and verifier (source-ID labeled).

# TODO(phase 7): finalize the templates. Below are placeholder scaffolds; the reviewer
# must instruct the model to ground every claim in [S?] source ids only.
"""

from __future__ import annotations

REVIEW_SYSTEM_PROMPT = (
    "You are a careful research assistant. Write a literature review grounded ONLY in "
    "the provided sources. Every claim must cite one or more source ids like [S1]. "
    "Do not use any knowledge beyond the sources."
)  # TODO(phase 7): refine

VERIFIER_SYSTEM_PROMPT = (
    "You check whether a claim is entailed by its cited source passages. "
    "Answer with a structured supported/unsupported judgement."
)  # TODO(phase 7): refine


def build_review_user_prompt(query: str, sources: list[dict]) -> str:
    """Render the user prompt with the labeled source block."""
    raise NotImplementedError  # TODO(phase 7)


def build_verifier_user_prompt(claim_text: str, sources: list[dict]) -> str:
    raise NotImplementedError  # TODO(phase 7)
