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
import random
import time
from collections.abc import AsyncIterator

import feedparser
import httpx

from citely.logging import get_logger

log = get_logger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"

# arXiv asks for a descriptive User-Agent; generic ones are rate-limited more aggressively.
_USER_AGENT = "citely/0.1 (literature-review ingest; +https://github.com/citely)"


class ArxivRateLimitError(RuntimeError):
    """Raised when arXiv keeps returning 429/5xx after exhausting retries."""

# The API caps max_results at 2000, but smaller pages are markedly more reliable.
_DEFAULT_PAGE_SIZE = 100
# Atom API will not page past this offset; beyond it, bulk data access is required.
# Public: the ingest pipeline uses it as its scan budget.
MAX_OFFSET = 30000


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
        max_retries: int = 6,
        max_backoff_s: float = 90.0,
    ) -> None:
        self._timeout = request_timeout_s
        self._min_interval = min_interval_s
        self._page_size = min(page_size, 2000)
        self._max_retries = max_retries
        self._max_backoff = max_backoff_s
        self._last_request_t = 0.0

    async def _throttle(self) -> None:
        """Sleep so consecutive requests are >= ``min_interval_s`` apart."""
        elapsed = time.monotonic() - self._last_request_t
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_t = time.monotonic()

    def _backoff(self, attempt: int, retry_after: float = 0.0) -> float:
        """Exponential backoff with jitter, never shorter than the server's Retry-After."""
        exp = self._min_interval * (2 ** (attempt - 1))
        return min(self._max_backoff, max(retry_after, exp)) + random.uniform(0, 1)

    @staticmethod
    def _retry_after(resp: httpx.Response) -> float:
        """Parse the ``Retry-After`` header (seconds) if present."""
        raw = resp.headers.get("retry-after")
        if not raw:
            return 0.0
        try:
            return float(raw)
        except ValueError:
            return 0.0

    async def _fetch_page(
        self, client: httpx.AsyncClient, search_query: str, start: int, count: int
    ) -> list[feedparser.FeedParserDict]:
        """Fetch one page, retrying on rate-limit/5xx/transport errors and empty feeds.

        Raises :class:`ArxivRateLimitError` if every attempt fails with a retryable HTTP
        error (so a throttled harvest surfaces loudly instead of silently yielding 0).
        Returns ``[]`` only for a genuinely empty feed after retries (end of results).
        """
        params: dict[str, str | int] = {
            "search_query": search_query,
            "start": start,
            "max_results": count,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        last_error: str | None = None
        for attempt in range(1, self._max_retries + 1):
            await self._throttle()
            try:
                resp = await client.get(ARXIV_API_URL, params=params)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status != 429 and status < 500:
                    # Non-retryable client error (bad query, etc.) — fail fast.
                    log.error("arxiv.page_fatal", start=start, status=status, error=str(exc))
                    raise
                wait = self._backoff(attempt, self._retry_after(exc.response))
                last_error = f"HTTP {status}"
                log.warning(
                    "arxiv.page_error",
                    start=start,
                    attempt=attempt,
                    status=status,
                    sleep_s=round(wait, 1),
                )
                await asyncio.sleep(wait)
                continue
            except httpx.HTTPError as exc:
                wait = self._backoff(attempt)
                last_error = str(exc)
                log.warning(
                    "arxiv.page_error",
                    start=start,
                    attempt=attempt,
                    error=str(exc),
                    sleep_s=round(wait, 1),
                )
                await asyncio.sleep(wait)
                continue

            feed = feedparser.parse(resp.content)
            entries = list(feed.entries)
            if entries:
                return entries
            # Valid response, no entries: could be a genuine end-of-results or a flaky
            # empty page. Retry a few times before treating it as the end.
            last_error = None
            log.warning("arxiv.empty_page", start=start, attempt=attempt)
            await asyncio.sleep(self._backoff(attempt))

        if last_error is not None:
            raise ArxivRateLimitError(
                f"arXiv request failed after {self._max_retries} attempts "
                f"(last error: {last_error}). The API is likely rate-limiting this IP; "
                f"wait a few minutes and retry, or lower the request rate."
            )
        return []

    async def search(self, categories: list[str], max_results: int) -> AsyncIterator[dict]:
        """Yield raw arXiv records for the given categories, newest first."""
        search_query = _build_search_query(categories)
        yielded = 0
        start = 0
        async with httpx.AsyncClient(
            timeout=self._timeout,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
        ) as client:
            while yielded < max_results and start < MAX_OFFSET:
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
