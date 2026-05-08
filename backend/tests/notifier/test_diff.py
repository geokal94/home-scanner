from types import SimpleNamespace

from home_scanner.notifier.diff import compute_alerts_to_send


def _listing(lid: int, price: int, bedrooms: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=lid, price_eur=price, bedrooms=bedrooms, is_active=True
    )


def _search(sid: int, **bounds) -> SimpleNamespace:
    return SimpleNamespace(id=sid, location_slug="x", is_active=True, **{
        "min_price": bounds.get("min_price"),
        "max_price": bounds.get("max_price"),
        "min_bedrooms": bounds.get("min_bedrooms"),
        "max_bedrooms": bounds.get("max_bedrooms"),
    })


def test_listing_within_bounds_is_alerted():
    s = _search(1, min_price=500, max_price=1000, min_bedrooms=1, max_bedrooms=3)
    listings = [_listing(101, price=800, bedrooms=2)]
    already_alerted = set()
    out = compute_alerts_to_send(s, listings, already_alerted_listing_ids=already_alerted)
    assert out == [(1, 101)]


def test_listing_already_alerted_is_skipped():
    s = _search(1, max_price=1000)
    listings = [_listing(101, price=800, bedrooms=2)]
    out = compute_alerts_to_send(s, listings, already_alerted_listing_ids={101})
    assert out == []


def test_listing_above_max_price_is_skipped():
    s = _search(1, max_price=700)
    listings = [_listing(101, price=800, bedrooms=2)]
    out = compute_alerts_to_send(s, listings, already_alerted_listing_ids=set())
    assert out == []


def test_listing_below_min_bedrooms_is_skipped():
    s = _search(1, min_bedrooms=2)
    listings = [_listing(101, price=800, bedrooms=1)]
    out = compute_alerts_to_send(s, listings, already_alerted_listing_ids=set())
    assert out == []


def test_listing_with_null_bedrooms_passes_bounds():
    """Null bedrooms shouldn't exclude — Spitogatos sometimes omits the field."""
    s = _search(1, min_bedrooms=2, max_bedrooms=2)
    listings = [_listing(101, price=800, bedrooms=None)]
    out = compute_alerts_to_send(s, listings, already_alerted_listing_ids=set())
    assert out == [(1, 101)]


def test_inactive_listing_is_skipped():
    s = _search(1)
    listing = _listing(101, price=800, bedrooms=2)
    listing.is_active = False
    out = compute_alerts_to_send(s, [listing], already_alerted_listing_ids=set())
    assert out == []
