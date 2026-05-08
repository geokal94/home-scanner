"""Spitogatos scraper module."""
from .client import ScrapeError, SpitogatosClient
from .models import ScrapedListing, SearchFilter
from .service import scrape_search

__all__ = [
    "ScrapeError",
    "ScrapedListing",
    "SearchFilter",
    "SpitogatosClient",
    "scrape_search",
]
