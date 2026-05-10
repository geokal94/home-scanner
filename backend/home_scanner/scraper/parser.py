"""Parse Spitogatos rental search results into ScrapedListing rows.

Selectors target the current Spitogatos rental search markup (Nuxt-rendered).
When Spitogatos changes the markup, the breakage is localised to this file
and the test fixture in tests/fixtures/spitogatos/.

Card structure (real example):
    <article class="ordered-element">
      <div class="tile ...">
        <a href="/aggelia/2118810894" class="tile__link">…</a>
        <h3 class="tile__title">Studio / Γκαρσονιέρα, 32τ.μ.</h3>
        <h3 class="tile__location">Αντιγονιδών (Κέντρο Θεσσαλονίκης)</h3>
        <div class="tile__price"><p class="price__text">€480 / μήνα</p></div>
      </div>
    </article>
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from .models import ScrapedListing

_HREF_ID_RE = re.compile(r"^/aggelia/(\d+)$")
_PRICE_RE = re.compile(r"€\s*([\d.,]+)")
# Greek "τ.μ." abbreviation for square metres; tolerate space and stray punctuation.
_AREA_RE = re.compile(r"(\d+)\s*τ\.?\s*μ", re.IGNORECASE)


def parse_listings(html: str) -> list[ScrapedListing]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[ScrapedListing] = []
    for card in soup.find_all("article", class_="ordered-element"):
        listing = _parse_card(card)
        if listing is not None:
            out.append(listing)
    return out


def _parse_card(card: Tag) -> ScrapedListing | None:
    # Listing ID + URL come from the tile link (`/aggelia/<numeric_id>`).
    link = card.find("a", class_="tile__link", href=True)
    if not isinstance(link, Tag):
        return None
    href = link.get("href", "")
    if not isinstance(href, str):
        return None
    match_id = _HREF_ID_RE.match(href)
    if not match_id:
        return None
    external_id = match_id.group(1)
    url = f"https://www.spitogatos.gr{href}"

    price = _extract_price(card)
    if price is None:
        return None

    title = _text_in(card, "h3", "tile__title")
    location_text = _text_in(card, "h3", "tile__location")
    area_m2 = _extract_area(title) if title else None
    bedrooms = _infer_bedrooms(title) if title else None

    return ScrapedListing(
        external_id=external_id,
        url=url,
        title=title,
        price_eur=price,
        bedrooms=bedrooms,
        area_m2=area_m2,
        location_text=location_text,
    )


def _extract_price(card: Tag) -> int | None:
    """Match `€480 / μήνα` or `€1.250 / μήνα` inside `<p class="price__text">`."""
    el = card.find("p", class_="price__text")
    if not isinstance(el, Tag):
        return None
    match = _PRICE_RE.search(el.get_text(strip=True))
    if not match:
        return None
    raw = match.group(1).replace(".", "").replace(",", "")
    try:
        return int(raw)
    except ValueError:
        return None


def _extract_area(title: str) -> int | None:
    match = _AREA_RE.search(title)
    return int(match.group(1)) if match else None


def _infer_bedrooms(title: str) -> int | None:
    """Title gives us studio (=0 bedrooms) but not other counts.

    Greek 'Studio / Γκαρσονιέρα' both mean studio. For non-studio types
    ('Διαμέρισμα', 'Μεζονέτα'), bedroom count isn't on the search card —
    it's only on the listing detail page, out of scope for the MVP scraper.
    """
    lowered = title.lower()
    if "studio" in lowered or "γκαρσονιέρα" in lowered:
        return 0
    return None


def _text_in(card: Tag, tag: str, css_class: str) -> str | None:
    el = card.find(tag, class_=css_class)
    if not isinstance(el, Tag):
        return None
    text = el.get_text(strip=True)
    return text or None
