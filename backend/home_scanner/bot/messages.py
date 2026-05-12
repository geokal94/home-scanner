"""Outgoing-message formatting (Telegram MarkdownV2-safe)."""
from __future__ import annotations


def escape_md(text: str) -> str:
    """Escape MarkdownV2 metacharacters in body text. Telegram's escape rules are strict."""
    chars = r"_*[]()~`>#+-=|{}.!"
    return "".join("\\" + c if c in chars else c for c in text)


def escape_md_url(url: str) -> str:
    """Escape only `)` and `\\` — the only metacharacters allowed inside MarkdownV2 link parens.

    Body-text escaping (escape_md) over-escapes URLs and breaks rendering: Telegram does
    not strip backslashes from `\\.` etc. inside `(...)`, so the link target ends up
    containing literal backslashes and won't open.
    """
    return url.replace("\\", "\\\\").replace(")", "\\)")


def format_listing_alert(
    *,
    price_eur: int,
    bedrooms: int | None,
    area_m2: int | None,
    location_text: str | None,
    url: str,
) -> str:
    bedrooms_str = f"{bedrooms} BR" if bedrooms is not None else "—"
    area_str = f" · {area_m2} m²" if area_m2 is not None else ""
    location = location_text or ""
    return (
        f"🏠 *€{price_eur:,}* · {escape_md(bedrooms_str)}{escape_md(area_str)}\n"
        f"{escape_md(location)}\n"
        f"[View on xe\\.gr →]({escape_md_url(url)})"
    )
