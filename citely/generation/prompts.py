"""Prompt templates for the reviewer and verifier (source-ID labeled).

The reviewer emits *atomic claims*, each grounded in one or more labeled source ids; the
verifier judges entailment of a single claim against its cited sources. Both are used with
``generate_json`` so the model returns structured output rather than free prose.
"""

from __future__ import annotations

REVIEW_SYSTEM_PROMPT = (
    "You are a careful research assistant writing a short literature review. "
    "Ground every statement ONLY in the provided sources; never use outside knowledge or "
    "invent facts. Break the review into atomic claims: each claim is a single, verifiable "
    "statement attributable to one or more of the given source ids. Cite the source ids "
    "(e.g. S1, S2) that support each claim. Omit any claim you cannot attribute to a source."
)

VERIFIER_SYSTEM_PROMPT = (
    "You are a strict fact-checker. Decide whether the CLAIM is fully entailed by the "
    "provided source passages. Mark it supported only if the sources directly state or "
    "clearly imply the claim; if they are silent or contradict it, mark it unsupported. "
    "Judge using the sources alone, not outside knowledge."
)


def _format_source_block(sources: list[dict]) -> str:
    """Render labeled sources as ``[S1] (Title, Year) text`` lines."""
    lines = []
    for source in sources:
        sid = source.get("id", "?")
        meta = ""
        title = source.get("title")
        if title:
            year = source.get("year")
            meta = f" ({title}, {year})" if year else f" ({title})"
        lines.append(f"[{sid}]{meta} {source.get('text', '').strip()}")
    return "\n\n".join(lines)


def build_review_user_prompt(query: str, sources: list[dict]) -> str:
    """Render the user prompt with the labeled source block."""
    return (
        f"Question: {query}\n\n"
        f"Sources:\n{_format_source_block(sources)}\n\n"
        "Write the literature review as a list of grounded claims. For each claim provide "
        "its text and the source ids it is grounded in."
    )


def build_verifier_user_prompt(claim_text: str, sources: list[dict]) -> str:
    return (
        f"Claim: {claim_text}\n\n"
        f"Sources:\n{_format_source_block(sources)}\n\n"
        "Is the claim fully supported by these sources?"
    )
