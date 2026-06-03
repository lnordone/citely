"""Async arXiv API client with backoff + rate limiting.

Queries the arXiv Atom API (``export.arxiv.org/api/query``), pages through results with
``start``/``max_results``, respects the ~3s politeness interval, and retries flaky/empty
responses (the API is known to intermittently return valid-but-empty feeds).

Categories use the ``cat:`` prefix and support wildcards, e.g. ``cs.*`` (all of computer
science) or ``eess.*`` (electrical engineering & systems science). The category list is
OR'd together into one ``search_query``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

import feedparser
import httpx

from citely.logging import get_logger

log = get_logger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"

# The API caps max_results at 2000, but smaller pages are markedly more reliable.
_DEFAULT_PAGE_SIZE = 100
# Atom API will not page past this offset; beyond it, bulk data access is required.
_MAX_OFFSET = 30000


def _build_search_query(categories: list[str]) -> str:
    """OR the categories into a single ``cat:`` query (wildcards allowed)."""
    if not categories:
        raise ValueError("at least one category is required")
    return " OR ".join(f"cat:{c}" for c in categories)


def _entry_to_record(entry: feedparser.FeedParserDict) -> dict:
    """Project a feedparser entry into a plain dict (insulates normalize from feedparser)."""
    pdf_url = ""
    for link in entry.get("links", []):
        if link.get("type") == "application/pdf" or link.get("title") == "pdf":
            pdf_url = link.get("href", "")
            break
    return {
        "id": entry.get("id", ""),
        "title": entry.get("title", ""),
        "summary": entry.get("summary", ""),
        "authors": [a.get("name", "") for a in entry.get("authors", [])],
        "categories": [t.get("term", "") for t in entry.get("tags", [])],
        "published": entry.get("published", ""),
        "pdf_url": pdf_url,
    }


class ArxivClient:
    def __init__(
        self,
        request_timeout_s: float = 30.0,
        min_interval_s: float = 3.0,
        page_size: int = _DEFAULT_PAGE_SIZE,
        max_retries: int = 4,
    ) -> None:
        self._timeout = request_timeout_s
        self._min_interval = min_interval_s
        self._page_size = min(page_size, 2000)
        self._max_retries = max_retries
        self._last_request_t = 0.0

    async def _throttle(self) -> None:
        """Sleep so consecutive requests are >= ``min_interval_s`` apart."""
        elapsed = time.monotonic() - self._last_request_t
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_t = time.monotonic()

    async def _fetch_page(
        self, client: httpx.AsyncClient, search_query: str, start: int, count: int
    ) -> list[feedparser.FeedParserDict]:
        """Fetch one page, retrying on transport errors and empty-but-valid feeds."""
        params: dict[str, str | int] = {
            "search_query": search_query,
            "start": start,
            "max_results": count,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        for attempt in range(1, self._max_retries + 1):
            await self._throttle()
            try:
                resp = await client.get(ARXIV_API_URL, params=params)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                log.warning("arxiv.page_error", start=start, attempt=attempt, error=str(exc))
                await asyncio.sleep(self._min_interval * attempt)
                continue
            feed = feedparser.parse(resp.content)
            entries = list(feed.entries)
            if entries:
                return entries
            # Valid response, no entries: could be a genuine end-of-results or a flaky
            # empty page. Retry a few times before treating it as the end.
            log.warning("arxiv.empty_page", start=start, attempt=attempt)
            await asyncio.sleep(self._min_interval * attempt)
        return []

    async def search(
        self, categories: list[str], max_results: int
    ) -> AsyncIterator[dict]:
        """Yield raw arXiv records for the given categories, newest first."""
        search_query = _build_search_query(categories)
        yielded = 0
        start = 0
        async with httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": "citely/0.1 (arxiv ingest)"},
            follow_redirects=True,
        ) as client:
            while yielded < max_results and start < _MAX_OFFSET:
                count = min(self._page_size, max_results - yielded)
                entries = await self._fetch_page(client, search_query, start, count)
                if not entries:
                    break
                for entry in entries:
                    yield _entry_to_record(entry)
                    yielded += 1
                    if yielded >= max_results:
                        break
                start += len(entries)
        log.info("arxiv.search_done", yielded=yielded, categories=categories)
