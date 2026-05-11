from urllib.parse import parse_qs, urlparse

from home_scanner.scraper.models import SearchFilter
from home_scanner.scraper.search_url import build_search_url

# Stable Google Place ID for Thessaloniki on xe.gr.
PLACE_ID_THESSALONIKI = "ChIJ7eAoFPQ4qBQRqXTVuBXnugk"


def test_url_targets_xe_rental_results():
    f = SearchFilter(location_slug=PLACE_ID_THESSALONIKI)
    url = build_search_url(f)
    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "www.xe.gr"
    assert parsed.path == "/property/results"


def test_url_includes_required_filters():
    f = SearchFilter(location_slug=PLACE_ID_THESSALONIKI)
    url = build_search_url(f)
    qs = parse_qs(urlparse(url).query)
    assert qs["item_type"] == ["re_residence"]
    assert qs["transaction_name"] == ["rent"]
    assert qs["geo_place_ids[]"] == [PLACE_ID_THESSALONIKI]


def test_url_ignores_price_and_bedroom_filters():
    """Price and bedrooms are intentionally filtered DB-side, not via URL.
    Passing them should not change the URL — the upstream filter param contract
    on xe.gr is unstable, so we don't depend on it."""
    f = SearchFilter(
        location_slug=PLACE_ID_THESSALONIKI,
        min_price=600,
        max_price=1200,
        min_bedrooms=2,
        max_bedrooms=3,
    )
    url = build_search_url(f)
    qs = parse_qs(urlparse(url).query)
    assert "minimum_price" not in qs
    assert "maximum_price" not in qs
    assert "bedrooms" not in qs


def test_url_uses_percent_encoded_brackets():
    f = SearchFilter(location_slug=PLACE_ID_THESSALONIKI)
    url = build_search_url(f)
    # urlencode percent-encodes '[' and ']' to %5B/%5D
    assert "geo_place_ids%5B%5D=" in url
