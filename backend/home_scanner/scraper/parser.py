# ruff: noqa: RUF002, RUF003  # Greek + × characters are intentional in docstrings/comments
"""Parse xe.gr rental search results into ScrapedListing rows.

Selectors target the current xe.gr property-results markup. When xe.gr changes
the markup, the breakage is localised to this file and the test fixture in
tests/fixtures/xe/.

Card structure (real example, see tests/fixtures/xe/thessaloniki-page1.html):
    <div class="common-ad" id="common_property_ad_<UUID>">
      <div class="common-ad-image-container">
        <a href="https://www.xe.gr/property/d/enoikiaseis-katoikion/<UUID>/<slug>?…">
          <picture>…<img alt="Ενοικίαση κατοικίας Θεσσαλονίκη (...) Διαμέρισμα 55 τ.μ." …></picture>
        </a>
      </div>
      <div class="common-ad-body">
        <a href="…same URL…">
          <div class="common-property-ad-title"><h3>Διαμέρισμα 55 τ.μ.</h3></div>
          <div class="common-property-ad-price">
            <span class="property-ad-price">550 €</span>
            …
          </div>
          <div class="common-property-ad-details">
            <span class="property-ad-level">4ος</span>
            <div class="property-ad-detail-container">
              <i class="xe xe-bedroom"></i><span>×1</span>
            </div>
            <div class="property-ad-detail-container">
              <i class="xe xe-bathroom"></i><span>×1</span>
            </div>
          </div>
          <h3 class="common-property-ad-address">Θεσσαλονίκη (Χαριλάου) | Ενοικίαση κατοικίας</h3>
        </a>
      </div>
    </div>
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from .models import ScrapedListing

_UUID_RE = re.compile(
    r"/property/d/enoikiaseis-katoikion/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)
_PRICE_RE = re.compile(r"([\d.,]+)\s*€")
_AREA_RE = re.compile(r"(\d+)\s*τ\.?\s*μ", re.IGNORECASE)


def parse_listings(html: str) -> list[ScrapedListing]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[ScrapedListing] = []
    for card in soup.find_all("div", class_="common-ad"):
        listing = _parse_card(card)
        if listing is not None:
            out.append(listing)
    return out


def _parse_card(card: Tag) -> ScrapedListing | None:
    # Listing ID + URL come from the first anchor pointing at /property/d/...
    link = _find_listing_link(card)
    if link is None:
        return None
    href = link.get("href", "")
    if not isinstance(href, str):
        return None
    match_id = _UUID_RE.search(href)
    if not match_id:
        return None
    external_id = match_id.group(1)
    url = href if href.startswith("http") else f"https://www.xe.gr{href}"

    price = _extract_price(card)
    if price is None:
        return None

    title = _text_in(card, "div", "common-property-ad-title")
    location_text = _text_in(card, "h3", "common-property-ad-address")
    area_m2 = _extract_area(title) if title else None
    bedrooms = _extract_bedrooms(card)

    return ScrapedListing(
        external_id=external_id,
        url=url,
        title=title,
        price_eur=price,
        bedrooms=bedrooms,
        area_m2=area_m2,
        location_text=location_text,
    )


def _find_listing_link(card: Tag) -> Tag | None:
    for a in card.find_all("a", href=True):
        if isinstance(a, Tag) and _UUID_RE.search(a.get("href", "") or ""):
            return a
    return None


def _extract_price(card: Tag) -> int | None:
    """Match `550 €` or `1.250 €` inside `<span class="property-ad-price">`."""
    el = card.find("span", class_="property-ad-price")
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


def _extract_bedrooms(card: Tag) -> int | None:
    """Bedrooms shown as `<i class="xe-bedroom"></i><span>×N</span>` in details."""
    bedroom_icon = card.find("i", class_="xe-bedroom")
    if not isinstance(bedroom_icon, Tag):
        return None
    # The bedroom count sits in the next <span> sibling, formatted as "×N"
    sibling = bedroom_icon.find_next_sibling("span")
    if not isinstance(sibling, Tag):
        return None
    text = sibling.get_text(strip=True)
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def _text_in(card: Tag, tag: str, css_class: str) -> str | None:
    el = card.find(tag, class_=css_class)
    if not isinstance(el, Tag):
        return None
    text = el.get_text(separator=" ", strip=True)
    return text or None
