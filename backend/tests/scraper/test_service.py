from unittest.mock import Mock

from home_scanner.scraper.models import SearchFilter
from home_scanner.scraper.service import scrape_search

PLACE_ID = "ChIJ7eAoFPQ4qBQRqXTVuBXnugk"  # Thessaloniki


def test_scrape_search_calls_client_with_built_url_and_returns_parsed():
    """Service orchestrator: build URL → fetch → parse. URL must include the
    Place ID; result must contain the parsed listing(s)."""
    fake_html = """
    <html><body>
    <div class="common-ad">
      <a href="https://www.xe.gr/property/d/enoikiaseis-katoikion/11111111-2222-3333-4444-555555555555/title-700-32">link</a>
      <div class="common-property-ad-title"><h3>Studio 32 τ.μ.</h3></div>
      <span class="property-ad-price">700 €</span>
    </div>
    </body></html>
    """
    client = Mock()
    client.fetch.return_value = fake_html

    f = SearchFilter(location_slug=PLACE_ID, max_price=1000)
    listings = scrape_search(f, client=client)

    args, _ = client.fetch.call_args
    assert "xe.gr/property/results" in args[0]
    assert PLACE_ID in args[0]
    assert "transaction_name=rent" in args[0]

    assert len(listings) == 1
    assert listings[0].external_id == "11111111-2222-3333-4444-555555555555"
    assert listings[0].price_eur == 700
