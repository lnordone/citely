"""Raw arXiv API record -> Paper (dedup key = arxiv id).

# TODO(phase 3): map Atom fields, strip versions from ids, parse dates/authors/categories.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from citely.db.models import Paper


def normalize_record(record: dict) -> Paper:
    """Convert one raw arXiv record into a Paper ORM instance."""
    raise NotImplementedError  # TODO(phase 3)
