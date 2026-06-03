"""Async arXiv API client with backoff + rate limiting.

# TODO(phase 3): query the arXiv Atom API, paginate, respect the ~3s rate limit, retry.
"""

from __future__ import annotations

from collections.abc import AsyncIterator


class ArxivClient:
    def __init__(self, request_timeout_s: float = 30.0, min_interval_s: float = 3.0) -> None:
        self._timeout = request_timeout_s
        self._min_interval = min_interval_s

    async def search(
        self, categories: list[str], max_results: int
    ) -> AsyncIterator[dict]:
        """Yield raw arXiv records for the given categories."""
        raise NotImplementedError  # TODO(phase 3)
        yield {}  # pragma: no cover - keeps this a valid async generator
