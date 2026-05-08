from home_scanner.scraper.models import SearchFilter
from home_scanner.scraper.search_url import build_search_url


def test_minimal_filter_uses_location_only():
    f = SearchFilter(location_slug="marousi")
    assert build_search_url(f) == "https://www.spitogatos.gr/enoikiaseis-katoikies/marousi"


def test_with_price_range():
    f = SearchFilter(location_slug="athina-kentro", min_price=600, max_price=1200)
    url = build_search_url(f)
    assert url.startswith("https://www.spitogatos.gr/enoikiaseis-katoikies/athina-kentro?")
    assert "priceMin=600" in url
    assert "priceMax=1200" in url


def test_with_bedrooms_range():
    f = SearchFilter(location_slug="thessaloniki", min_bedrooms=2, max_bedrooms=3)
    url = build_search_url(f)
    assert "bedroomsMin=2" in url
    assert "bedroomsMax=3" in url


def test_only_min_bound():
    f = SearchFilter(location_slug="marousi", min_price=800)
    url = build_search_url(f)
    assert "priceMin=800" in url
    assert "priceMax" not in url
