from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from home_scanner.db.models import Listing, SavedSearch, User
from home_scanner.db.repositories import (
    create_saved_search,
    get_or_create_user,
    listing_ids_already_alerted,
    upsert_listing,
)
from home_scanner.notifier.dispatch import dispatch_alerts
from sqlalchemy.orm import Session


@pytest.mark.asyncio
async def test_dispatch_sends_messages_and_records_alerts(db_session: Session):
    user = get_or_create_user(db_session, telegram_chat_id=42, telegram_username=None)
    search = create_saved_search(db_session, user_id=user.id, location_slug="x")
    db_session.flush()

    listing = upsert_listing(
        db_session,
        now=datetime.now(UTC),
        external_id="ext-1",
        url="https://x/1",
        title="t",
        price_eur=900,
        bedrooms=2,
        area_m2=70,
        location_text="Athens",
    )
    db_session.flush()

    bot = AsyncMock()
    bot.send_message.return_value.message_id = 12345

    sent = await dispatch_alerts(
        db_session,
        bot=bot,
        alerts=[(search.id, listing.id)],
        chat_id_for_search={search.id: user.telegram_chat_id},
        now=datetime.now(UTC),
    )

    assert sent == 1
    bot.send_message.assert_awaited_once()
    assert listing_ids_already_alerted(db_session, search_id=search.id) == {listing.id}


@pytest.mark.asyncio
async def test_dispatch_skips_user_blocked_bot(db_session: Session):
    from telegram.error import Forbidden

    user = get_or_create_user(db_session, telegram_chat_id=43, telegram_username=None)
    search = create_saved_search(db_session, user_id=user.id, location_slug="x")
    db_session.flush()
    listing = upsert_listing(
        db_session, now=datetime.now(UTC),
        external_id="ext-2", url="https://x/2", title=None,
        price_eur=900, bedrooms=2, area_m2=None, location_text=None,
    )
    db_session.flush()

    bot = AsyncMock()
    bot.send_message.side_effect = Forbidden("bot was blocked by the user")

    sent = await dispatch_alerts(
        db_session, bot=bot,
        alerts=[(search.id, listing.id)],
        chat_id_for_search={search.id: user.telegram_chat_id},
        now=datetime.now(UTC),
    )
    assert sent == 0
    db_session.refresh(user)
    assert user.deactivated_at is not None
