"""Build xe.gr rental-search URLs from a SearchFilter.

xe.gr URL shape:
    https://www.xe.gr/property/results
        ?item_type=re_residence
        &transaction_name=rent
        &geo_place_ids%5B%5D=<google_place_id>

The location identifier stored on `SearchFilter.location_slug` is the Google
Place ID used by xe.gr's `geo_place_ids[]` query parameter (see locations.yml).

Price and bedroom filters are applied DB-side after scraping rather than via
URL params — keeps the URL shape simple and avoids depending on xe.gr's
private filter param contract.
"""
from __future__ import annotations

from urllib.parse import urlencode

from .models import SearchFilter

_BASE = "https://www.xe.gr/property/results"


def build_search_url(f: SearchFilter) -> str:
    params: list[tuple[str, str]] = [
        ("item_type", "re_residence"),
        ("transaction_name", "rent"),
        ("geo_place_ids[]", f.location_slug),
    ]
    return f"{_BASE}?{urlencode(params)}"
