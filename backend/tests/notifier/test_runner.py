from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from home_scanner.db.models import ScrapeRun
from home_scanner.db.repositories import (
    create_saved_search,
    get_or_create_user,
)
from home_scanner.notifier.runner import run_one_scrape_cycle
from home_scanner.scraper.models import ScrapedListing
from sqlalchemy.orm import Session


@pytest.mark.asyncio
async def test_run_one_cycle_records_run_and_alerts(db_session: Session):
    user = get_or_create_user(db_session, telegram_chat_id=11, telegram_username=None)
    create_saved_search(db_session, user_id=user.id, location_slug="marousi")
    db_session.flush()

    scraper = Mock()
    scraper.return_value = [
        ScrapedListing(
            external_id="ext-1", url="https://x/1", title="t",
            price_eur=900, bedrooms=2, area_m2=60, location_text="Marousi",
        )
    ]
    bot = AsyncMock()
    bot.send_message.return_value.message_id = 1

    summary = await run_one_scrape_cycle(
        session=db_session,
        bot=bot,
        scrape_search_fn=scraper,
        now=datetime.now(UTC),
    )

    assert summary.searches_processed == 1
    assert summary.listings_seen == 1
    assert summary.new_alerts == 1
    assert bot.send_message.await_count == 1

    # ScrapeRun row written
    runs = db_session.query(ScrapeRun).all()
    assert len(runs) == 1
    assert runs[0].status == "ok"


@pytest.mark.asyncio
async def test_run_one_cycle_isolates_per_search_failures(db_session: Session):
    user = get_or_create_user(db_session, telegram_chat_id=12, telegram_username=None)
    create_saved_search(db_session, user_id=user.id, location_slug="marousi")
    create_saved_search(db_session, user_id=user.id, location_slug="kallithea")
    db_session.flush()

    from home_scanner.scraper import ScrapeError
    def scraper(f, client=None):
        if f.location_slug == "marousi":
            raise ScrapeError("503")
        return [
            ScrapedListing(
                external_id="ok", url="https://x/ok", title=None,
                price_eur=800, bedrooms=2, area_m2=None, location_text=None,
            )
        ]
    bot = AsyncMock()
    bot.send_message.return_value.message_id = 1

    summary = await run_one_scrape_cycle(
        session=db_session,
        bot=bot,
        scrape_search_fn=scraper,
        now=datetime.now(UTC),
    )
    assert summary.searches_processed == 2
    assert "marousi" in summary.errors["failed"]

    runs = db_session.query(ScrapeRun).all()
    assert runs[0].status == "ok"  # partial failure → still 'ok' (not catastrophic)
    assert runs[0].errors == {"failed": {"marousi": "503"}}


@pytest.mark.asyncio
async def test_run_one_cycle_flags_zero_listings_on_200(db_session: Session):
    """Spec §8 #1 maintenance-risk canary: HTTP 200 + parser returned 0 listings
    is almost always a layout change. Record it as a failed entry per-search."""
    user = get_or_create_user(db_session, telegram_chat_id=13, telegram_username=None)
    create_saved_search(db_session, user_id=user.id, location_slug="marousi")
    db_session.flush()

    scraper = Mock()
    scraper.return_value = []  # 200 OK but parser found nothing
    bot = AsyncMock()

    summary = await run_one_scrape_cycle(
        session=db_session,
        bot=bot,
        scrape_search_fn=scraper,
        now=datetime.now(UTC),
    )

    assert summary.searches_processed == 1
    assert summary.listings_seen == 0
    assert summary.new_alerts == 0
    assert summary.errors["failed"] == {"marousi": "zero_listings_on_200"}
    assert bot.send_message.await_count == 0

    runs = db_session.query(ScrapeRun).all()
    assert runs[0].errors == {"failed": {"marousi": "zero_listings_on_200"}}
