"""Parse Spitogatos rental search results into ScrapedListing rows.

Selectors are intentionally narrow and well-named so that when Spitogatos changes
the markup, the breakage is localised here.
"""
from __future__ import annotations

import re
from typing import Iterable

from bs4 import BeautifulSoup, Tag

from .models import ScrapedListing

_PRICE_RE = re.compile(r"(\d[\d.,]*)")
_BEDROOMS_RE = re.compile(r"(\d+)\s*bedroom", re.IGNORECASE)
_AREA_RE = re.compile(r"(\d+)\s*m²", re.IGNORECASE)


def parse_listings(html: str) -> list[ScrapedListing]:
    soup = BeautifulSoup(html, "html.parser")
    cards: Iterable[Tag] = soup.find_all("article", class_="ordered-element")
    out: list[ScrapedListing] = []
    for card in cards:
        listing = _parse_card(card)
        if listing is not None:
            out.append(listing)
    return out


def _parse_card(card: Tag) -> ScrapedListing | None:
    external_id = card.get("data-listing-id")
    if not external_id:
        return None

    price = _extract_price(card)
    if price is None:
        # No price → skip; the alert flow needs price to filter
        return None

    link = card.find("a", href=True)
    href = link["href"] if isinstance(link, Tag) else None
    if not href:
        return None
    url = href if href.startswith("http") else f"https://www.spitogatos.gr{href}"

    return ScrapedListing(
        external_id=str(external_id),
        url=url,
        title=_text_or_none(card, "h3"),
        price_eur=price,
        bedrooms=_extract_int(card, "tile__bedrooms", _BEDROOMS_RE),
        area_m2=_extract_int(card, "tile__area", _AREA_RE),
        location_text=_text_or_none(card, "tile__location"),
    )


def _extract_price(card: Tag) -> int | None:
    div = card.find("div", class_="tile__price")
    if not isinstance(div, Tag):
        return None
    match = _PRICE_RE.search(div.get_text(strip=True))
    if not match:
        return None
    return int(match.group(1).replace(".", "").replace(",", ""))


def _extract_int(card: Tag, css_class: str, pattern: re.Pattern[str]) -> int | None:
    el = card.find(class_=css_class)
    if not isinstance(el, Tag):
        return None
    match = pattern.search(el.get_text())
    return int(match.group(1)) if match else None


def _text_or_none(card: Tag, css_class_or_tag: str) -> str | None:
    if css_class_or_tag.startswith("tile__"):
        el = card.find(class_=css_class_or_tag)
    else:
        el = card.find(css_class_or_tag)
    if not isinstance(el, Tag):
        return None
    text = el.get_text(strip=True)
    return text or None
