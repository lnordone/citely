"""Claims JSON -> markdown with inline citations + bibliography.

Every ``[S?]`` marker emitted maps to a real cited source (ids absent from ``sources``
are dropped), and the bibliography lists exactly the sources that were cited — so a
rendered review never contains a dangling citation.
"""

from __future__ import annotations

import re

from citely.retrieval.types import Claim, PaperRef, RetrievedPassage

_SID_NUM_RE = re.compile(r"\d+")


def _sid_sort_key(sid: str) -> tuple[int, str]:
    match = _SID_NUM_RE.search(sid)
    return (int(match.group()) if match else 1_000_000, sid)


def _format_citation(paper: PaperRef | None) -> str:
    if paper is None:
        return "(source metadata unavailable)"
    if not paper.authors:
        authors = "Unknown"
    elif len(paper.authors) == 1:
        authors = paper.authors[0]
    else:
        authors = f"{paper.authors[0]} et al."
    year = f" ({paper.year})" if paper.year else ""
    title = paper.title or "Untitled"
    url = f" {paper.url}" if paper.url else ""
    return f"{authors}{year}. *{title}*.{url}"


def render_markdown(claims: list[Claim], sources: list[RetrievedPassage]) -> str:
    """Render claims into cited markdown with a bibliography."""
    by_key = {s.source_key: s for s in sources if s.source_key}

    body_lines: list[str] = []
    cited_order: list[str] = []
    for claim in claims:
        cites = [sid for sid in claim.source_ids if sid in by_key]
        for sid in cites:
            if sid not in cited_order:
                cited_order.append(sid)
        marker = "".join(f"[{sid}]" for sid in cites)
        suffix = " *(unverified)*" if claim.supported is False else ""
        body_lines.append(f"{claim.text.strip()} {marker}{suffix}".strip())

    if not body_lines:
        return "_No grounded claims were produced._"

    body = "\n\n".join(body_lines)
    biblio = ["## Sources"]
    for sid in sorted(cited_order, key=_sid_sort_key):
        biblio.append(f"- **[{sid}]** {_format_citation(by_key[sid].paper)}")
    return f"{body}\n\n{chr(10).join(biblio)}"
