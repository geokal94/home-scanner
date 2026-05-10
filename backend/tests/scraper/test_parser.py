from pathlib import Path

from home_scanner.scraper.parser import parse_listings

FIXTURES = Path(__file__).parent.parent / "fixtures" / "spitogatos"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parses_real_thessaloniki_page():
    """Real spitogatos.gr rentals search HTML for Thessaloniki, captured 2026-05-10
    against the live deploy. 30 cards expected."""
    html = _load("thessaloniki-page1.html")
    listings = parse_listings(html)
    assert len(listings) == 30
    sample = listings[0]
    # `/aggelia/2118810894` → external_id "2118810894", url …spitogatos.gr/aggelia/2118810894
    assert sample.external_id.isdigit()
    assert sample.url.startswith("https://www.spitogatos.gr/aggelia/")
    assert sample.price_eur > 0
    assert sample.title  # Greek title — non-empty
    assert sample.location_text  # Greek location — non-empty
    assert sample.area_m2 is not None  # Every card has m² in title


def test_parses_studio_as_zero_bedrooms():
    """Real fixture: titles starting with 'Studio / Γκαρσονιέρα' should infer 0 bedrooms."""
    html = _load("thessaloniki-page1.html")
    listings = parse_listings(html)
    studios = [item for item in listings if item.title and "studio" in item.title.lower()]
    assert len(studios) > 0  # Real page has multiple studios
    for s in studios:
        assert s.bedrooms == 0


def test_parses_non_studio_as_unknown_bedrooms():
    """Διαμέρισμα/Μεζονέτα titles don't give bedroom count on the search card."""
    html = _load("thessaloniki-page1.html")
    listings = parse_listings(html)
    apartments = [
        item for item in listings
        if item.title
        and "studio" not in item.title.lower()
        and "γκαρσονιέρα" not in item.title.lower()
    ]
    assert len(apartments) > 0
    for a in apartments:
        assert a.bedrooms is None


def test_parses_empty_results_page():
    html = _load("empty-results.html")
    assert parse_listings(html) == []


def test_parser_skips_card_without_aggelia_link():
    """Cards without a /aggelia/<id> link can't be uniquely identified — skip."""
    html = """
    <html><body>
    <article class="ordered-element">
      <a href="/aggelia/111" class="tile__link">Link</a>
      <h3 class="tile__title">Studio, 32τ.μ.</h3>
      <h3 class="tile__location">Test</h3>
      <div class="tile__price"><p class="price__text">€800 / μήνα</p></div>
    </article>
    <article class="ordered-element">
      <a href="/something-else/222" class="tile__link">Wrong path</a>
      <div class="tile__price"><p class="price__text">€900 / μήνα</p></div>
    </article>
    </body></html>
    """
    listings = parse_listings(html)
    assert len(listings) == 1
    assert listings[0].external_id == "111"
    assert listings[0].price_eur == 800


def test_parser_skips_card_without_price():
    """Cards missing `<p class="price__text">` are skipped — alerts need price."""
    html = """
    <html><body>
    <article class="ordered-element">
      <a href="/aggelia/111" class="tile__link">Link</a>
      <h3 class="tile__title">Studio, 32τ.μ.</h3>
      <div class="tile__price"><p class="price__text">€800 / μήνα</p></div>
    </article>
    <article class="ordered-element">
      <a href="/aggelia/222" class="tile__link">Link</a>
      <h3 class="tile__title">Studio, 30τ.μ.</h3>
      <!-- no tile__price -->
    </article>
    </body></html>
    """
    listings = parse_listings(html)
    assert len(listings) == 1
    assert listings[0].external_id == "111"


def test_parser_handles_thousand_separators():
    """European pricing uses '.' as thousand separator: €1.250 → 1250."""
    html = """
    <html><body>
    <article class="ordered-element">
      <a href="/aggelia/333" class="tile__link">Link</a>
      <div class="tile__price"><p class="price__text">€1.250 / μήνα</p></div>
    </article>
    </body></html>
    """
    listings = parse_listings(html)
    assert listings[0].price_eur == 1250
