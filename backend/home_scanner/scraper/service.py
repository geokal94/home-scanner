"""Top-level scraper entrypoint: SearchFilter → list[ScrapedListing]."""
from __future__ import annotations

from .client import SpitogatosClient
from .models import ScrapedListing, SearchFilter
from .parser import parse_listings
from .search_url import build_search_url


def scrape_search(
    f: SearchFilter,
    client: SpitogatosClient,
) -> list[ScrapedListing]:
    url = build_search_url(f)
    html = client.fetch(url)
    return parse_listings(html)
