"""Pure logic: given a saved search, candidate listings, and the set of already-alerted
listing IDs, return the list of (saved_search_id, listing_id) tuples to alert.

This module knows nothing about the DB or Telegram — it's deterministic and unit-testable.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol


class _SavedSearchLike(Protocol):
    id: int
    is_active: bool
    min_price: int | None
    max_price: int | None
    min_bedrooms: int | None
    max_bedrooms: int | None


class _ListingLike(Protocol):
    id: int
    price_eur: int
    bedrooms: int | None
    is_active: bool


def compute_alerts_to_send(
    search: _SavedSearchLike,
    candidates: Iterable[_ListingLike],
    *,
    already_alerted_listing_ids: set[int],
) -> list[tuple[int, int]]:
    if not search.is_active:
        return []
    out: list[tuple[int, int]] = []
    for listing in candidates:
        if not listing.is_active:
            continue
        if listing.id in already_alerted_listing_ids:
            continue
        if not _matches(search, listing):
            continue
        out.append((search.id, listing.id))
    return out


def _matches(search: _SavedSearchLike, listing: _ListingLike) -> bool:
    if search.min_price is not None and listing.price_eur < search.min_price:
        return False
    if search.max_price is not None and listing.price_eur > search.max_price:
        return False
    # null bedrooms always passes — we don't have data, don't exclude
    if listing.bedrooms is not None:
        if search.min_bedrooms is not None and listing.bedrooms < search.min_bedrooms:
            return False
        if search.max_bedrooms is not None and listing.bedrooms > search.max_bedrooms:
            return False
    return True
