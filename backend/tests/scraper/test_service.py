from unittest.mock import Mock

from home_scanner.scraper.models import SearchFilter
from home_scanner.scraper.service import scrape_search


def test_scrape_search_calls_client_with_built_url_and_returns_parsed():
    fake_html = """
    <html><body>
    <article class="ordered-element" data-listing-id="999">
      <a href="/property/999">Link</a>
      <div class="tile__price">€700</div>
    </article>
    </body></html>
    """
    client = Mock()
    client.fetch.return_value = fake_html

    f = SearchFilter(location_slug="marousi", max_price=1000)
    listings = scrape_search(f, client=client)

    args, _ = client.fetch.call_args
    assert "marousi" in args[0]
    assert "priceMax=1000" in args[0]

    assert len(listings) == 1
    assert listings[0].external_id == "999"
    assert listings[0].price_eur == 700
