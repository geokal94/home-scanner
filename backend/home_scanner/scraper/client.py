"""HTTP client for fetching listing pages, with retry policy.

Targets xe.gr today; proxy support is preserved (via `proxy_url=`) for future
sources that need a residential IP.
"""
from __future__ import annotations

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "el-GR,el;q=0.9,en;q=0.8",
    "Referer": "https://www.xe.gr/",
}


class ScrapeError(Exception):
    """Raised when fetching a listing URL fails permanently."""


class _TransientServerError(Exception):
    """Internal — drives tenacity retries on 5xx (not on 403/429)."""


class ListingClient:
    """Thin wrapper around `httpx.Client` with retry-on-5xx and configurable proxy."""

    def __init__(self, proxy_url: str | None = None, timeout: float = 30.0) -> None:
        self._proxy_url = proxy_url
        self._timeout = timeout

    def fetch(self, url: str) -> str:
        try:
            return self._fetch_with_retries(url)
        except (RetryError, _TransientServerError) as exc:
            raise ScrapeError(f"Exhausted retries fetching {url}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(_TransientServerError),
        reraise=True,
    )
    def _fetch_with_retries(self, url: str) -> str:
        with httpx.Client(
            proxy=self._proxy_url,
            headers=_DEFAULT_HEADERS,
            timeout=self._timeout,
            follow_redirects=True,
        ) as client:
            resp = client.get(url)

        if 500 <= resp.status_code < 600:
            raise _TransientServerError(f"{resp.status_code} from {url}")
        if resp.status_code in (403, 429):
            raise ScrapeError(f"{resp.status_code} from {url} — bot detection")
        if resp.status_code != 200:
            raise ScrapeError(f"{resp.status_code} from {url}")
        return resp.text
