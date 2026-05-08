from pathlib import Path

from home_scanner.scraper.parser import parse_listings

FIXTURES = Path(__file__).parent.parent / "fixtures" / "spitogatos"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parses_real_athens_page():
    html = _load("athens-centre-page1.html")
    listings = parse_listings(html)
    assert len(listings) >= 5  # At least 5 listings on a centre-of-Athens page
    sample = listings[0]
    assert sample.external_id  # Non-empty
    assert sample.url.startswith("https://www.spitogatos.gr/")
    assert sample.price_eur > 0


def test_parses_empty_results_page():
    html = _load("empty-results.html")
    assert parse_listings(html) == []


def test_parser_skips_listings_without_price():
    # Construct minimal HTML with one good and one priceless card
    html = """
    <html><body>
    <article class="ordered-element" data-listing-id="111">
      <a href="/property/111">Link</a>
      <div class="tile__price">€800</div>
      <div class="tile__bedrooms">2 bedrooms</div>
    </article>
    <article class="ordered-element" data-listing-id="222">
      <a href="/property/222">Link</a>
      <!-- no price -->
    </article>
    </body></html>
    """
    listings = parse_listings(html)
    assert len(listings) == 1
    assert listings[0].external_id == "111"
    assert listings[0].price_eur == 800
