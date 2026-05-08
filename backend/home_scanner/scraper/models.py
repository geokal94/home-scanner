"""Domain models used by the scraper module."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchFilter:
    location_slug: str
    min_price: int | None = None
    max_price: int | None = None
    min_bedrooms: int | None = None
    max_bedrooms: int | None = None


@dataclass(frozen=True, slots=True)
class ScrapedListing:
    external_id: str
    url: str
    title: str | None
    price_eur: int
    bedrooms: int | None
    area_m2: int | None
    location_text: str | None
