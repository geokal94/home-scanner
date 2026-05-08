"""Build Spitogatos rental-search URLs from a SearchFilter."""
from __future__ import annotations

from urllib.parse import urlencode

from .models import SearchFilter

_BASE = "https://www.spitogatos.gr/enoikiaseis-katoikies"


def build_search_url(f: SearchFilter) -> str:
    base = f"{_BASE}/{f.location_slug}"

    params: list[tuple[str, str]] = []
    if f.min_price is not None:
        params.append(("priceMin", str(f.min_price)))
    if f.max_price is not None:
        params.append(("priceMax", str(f.max_price)))
    if f.min_bedrooms is not None:
        params.append(("bedroomsMin", str(f.min_bedrooms)))
    if f.max_bedrooms is not None:
        params.append(("bedroomsMax", str(f.max_bedrooms)))

    if not params:
        return base
    return f"{base}?{urlencode(params)}"
