from pathlib import Path

from home_scanner.scraper.parser import parse_listings

FIXTURES = Path(__file__).parent.parent / "fixtures" / "xe"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parses_real_thessaloniki_page():
    """Real xe.gr property/results page for Thessaloniki rentals, captured
    2026-05-11. Roughly 30+ ads expected (page shows 34 cards including non-listing
    promos; the parser keeps only those with a /property/d/ UUID and a price)."""
    html = _load("thessaloniki-page1.html")
    listings = parse_listings(html)
    assert len(listings) >= 20  # Solid lower bound; actual is higher
    sample = listings[0]
    # UUID regex: 8-4-4-4-12 hex
    assert len(sample.external_id) == 36 and sample.external_id.count("-") == 4
    assert sample.url.startswith("https://www.xe.gr/property/d/enoikiaseis-katoikion/")
    assert sample.price_eur > 0
    assert sample.location_text  # Greek address text
    assert sample.area_m2 is not None  # Every card has size in title


def test_parses_bedrooms_when_present():
    """xe.gr shows explicit bedroom count via xe-bedroom icon + count span."""
    html = _load("thessaloniki-page1.html")
    listings = parse_listings(html)
    with_bedrooms = [item for item in listings if item.bedrooms is not None]
    # The vast majority of real listings expose bedroom count
    assert len(with_bedrooms) >= 15
    # And all bedroom counts are sane integers
    for item in with_bedrooms:
        assert 0 <= item.bedrooms <= 20


def test_parses_empty_results_page():
    html = _load("empty-results.html")
    assert parse_listings(html) == []


def test_parser_skips_non_listing_common_ad():
    """xe.gr puts promotional 'common-ad' containers on the page that aren't
    listings (no /property/d/ link). Those must be skipped."""
    html = """
    <html><body>
    <div class="common-ad">
      <a href="/some/other/path">Promo banner</a>
      <span class="property-ad-price">999 €</span>
    </div>
    <div class="common-ad">
      <a href="https://www.xe.gr/property/d/enoikiaseis-katoikion/11111111-2222-3333-4444-555555555555/title-550-55">link</a>
      <div class="common-property-ad-title"><h3>Studio 32 τ.μ.</h3></div>
      <span class="property-ad-price">550 €</span>
    </div>
    </body></html>
    """
    listings = parse_listings(html)
    assert len(listings) == 1
    assert listings[0].external_id == "11111111-2222-3333-4444-555555555555"


def test_parser_handles_thousand_separators():
    """European pricing uses '.' as thousand separator: 1.250 → 1250."""
    html = """
    <html><body>
    <div class="common-ad">
      <a href="/property/d/enoikiaseis-katoikion/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/title">x</a>
      <span class="property-ad-price">1.250 €</span>
    </div>
    </body></html>
    """
    listings = parse_listings(html)
    assert listings[0].price_eur == 1250


def test_parser_skips_card_without_price():
    """Cards missing `<span class="property-ad-price">` are skipped — alerts need price."""
    html = """
    <html><body>
    <div class="common-ad">
      <a href="/property/d/enoikiaseis-katoikion/11111111-2222-3333-4444-555555555555/x">x</a>
      <!-- no price element -->
    </div>
    </body></html>
    """
    assert parse_listings(html) == []
