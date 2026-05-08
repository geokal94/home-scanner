"""HTTP client for Spitogatos via DataImpulse, with retry policy."""
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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) "
        "Gecko/20100101 Firefox/120.0"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.spitogatos.gr/",
}


class ScrapeError(Exception):
    """Raised when fetching a Spitogatos URL fails permanently."""


class _TransientServerError(Exception):
    """Internal — used to drive tenacity retries on 5xx-but-not-403/429."""


class SpitogatosClient:
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
            proxy=self._proxy_url, headers=_DEFAULT_HEADERS, timeout=self._timeout
        ) as client:
            resp = client.get(url)

        if 500 <= resp.status_code < 600:
            raise _TransientServerError(f"{resp.status_code} from {url}")
        if resp.status_code in (403, 429):
            raise ScrapeError(f"{resp.status_code} from {url} — bot detection")
        if resp.status_code != 200:
            raise ScrapeError(f"{resp.status_code} from {url}")
        return resp.text
