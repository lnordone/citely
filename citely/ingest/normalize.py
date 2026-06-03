"""Raw arXiv API record -> Paper (dedup key = arxiv id).

The arXiv id is normalized to its version-less form (``2401.00001v3`` -> ``2401.00001``)
so re-ingesting a new version of the same paper updates the existing row rather than
creating a duplicate.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from citely.db.models import Paper

# Matches the trailing version suffix on an arXiv id, e.g. "...00001v2".
_VERSION_RE = re.compile(r"v\d+$")
_WS_RE = re.compile(r"\s+")


def _arxiv_id(raw_id: str) -> str:
    """Extract the version-less arXiv id from an entry id URL.

    ``http://arxiv.org/abs/2401.00001v2`` -> ``2401.00001``
    (also handles old-style ids like ``http://arxiv.org/abs/cs/0501001v1`` ->
    ``cs/0501001``).
    """
    tail = raw_id.split("/abs/", 1)[-1] if "/abs/" in raw_id else raw_id
    return _VERSION_RE.sub("", tail.strip())


def _clean(text: str) -> str:
    """Collapse internal whitespace/newlines (arXiv wraps titles/abstracts)."""
    return _WS_RE.sub(" ", text).strip()


def _parse_published(value: str) -> date:
    """Parse an arXiv ISO-8601 published timestamp into a date."""
    if not value:
        raise ValueError("record is missing a 'published' date")
    # Examples: "2024-01-02T18:00:00Z" or with offset.
    cleaned = value.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned).date()


def normalize_record(record: dict) -> Paper:
    """Convert one raw arXiv record into a Paper ORM instance."""
    arxiv_id = _arxiv_id(record.get("id", ""))
    if not arxiv_id:
        raise ValueError(f"could not derive arxiv id from record: {record.get('id')!r}")
    return Paper(
        id=arxiv_id,
        title=_clean(record.get("title", "")),
        authors=[a for a in record.get("authors", []) if a],
        abstract=_clean(record.get("summary", "")),
        categories=[c for c in record.get("categories", []) if c],
        published=_parse_published(record.get("published", "")),
        pdf_url=record.get("pdf_url", "") or f"https://arxiv.org/pdf/{arxiv_id}",
    )
