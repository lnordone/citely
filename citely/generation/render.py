"""Claims JSON -> markdown with inline citations + bibliography.

# TODO(phase 7): render claim text with [S?] markers and a sources bibliography; every
# marker must map to a real source (covered by tests/test_render.py).
"""

from __future__ import annotations

from citely.retrieval.types import Claim, RetrievedPassage


def render_markdown(claims: list[Claim], sources: list[RetrievedPassage]) -> str:
    """Render claims into cited markdown with a bibliography."""
    raise NotImplementedError  # TODO(phase 7)
