from home_scanner.bot.messages import escape_md, escape_md_url, format_listing_alert


def test_escape_md_escapes_body_text_metacharacters():
    assert escape_md("Athens (Centre).") == r"Athens \(Centre\)\."


def test_escape_md_url_only_escapes_paren_and_backslash():
    """URLs in MarkdownV2 link parens must NOT have body-text escaping applied —
    Telegram doesn't unescape and the link breaks."""
    url = "https://www.xe.gr/property/d/enoikiaseis-katoikion/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/title"
    assert escape_md_url(url) == url


def test_escape_md_url_escapes_close_paren():
    url = "https://example.com/path)with-paren"
    assert escape_md_url(url) == r"https://example.com/path\)with-paren"


def test_format_listing_alert_keeps_url_clickable():
    out = format_listing_alert(
        price_eur=900,
        bedrooms=2,
        area_m2=70,
        location_text="Athens",
        url="https://www.xe.gr/property/d/enoikiaseis-katoikion/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/title",
    )
    assert "https://www.xe.gr/property/d/" in out
    assert r"https://www\.xe\.gr" not in out


def test_format_listing_alert_link_label_says_xe():
    out = format_listing_alert(
        price_eur=900, bedrooms=2, area_m2=70, location_text="Athens",
        url="https://www.xe.gr/property/d/x/y/z",
    )
    assert "View on xe" in out
    assert "spitogatos" not in out.lower()
