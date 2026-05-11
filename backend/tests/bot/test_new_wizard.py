"""Functional tests for the /new wizard. Uses the real ConversationHandler against
in-memory Telegram updates; the bot itself is mocked.
"""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session, sessionmaker

from home_scanner.bot.handlers.new_search import (
    BEDROOMS,
    LOCATION,
    PRICE_MAX,
    PRICE_MIN,
    handle_bedrooms,
    handle_location_text,
    handle_price_max,
    handle_price_min,
    start_new,
)
from home_scanner.db.repositories import list_user_saved_searches


def _fake_update(text: str | None = None, chat_id: int = 100):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_user.id = chat_id
    update.effective_user.username = "tester"
    update.effective_message.text = text
    update.effective_message.reply_text = AsyncMock()
    update.effective_message.reply_markdown_v2 = AsyncMock()
    update.message = update.effective_message
    return update


def _fake_context(session_factory: sessionmaker, user_data: dict | None = None):
    ctx = MagicMock()
    ctx.bot_data = {"session_factory": session_factory}
    ctx.user_data = user_data if user_data is not None else {}
    return ctx


@pytest.mark.asyncio
async def test_start_new_asks_for_location(db_engine):
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    update = _fake_update()
    ctx = _fake_context(sf)
    next_state = await start_new(update, ctx)
    assert next_state == LOCATION
    update.effective_message.reply_markdown_v2.assert_awaited_once()


@pytest.mark.asyncio
async def test_full_happy_path_creates_saved_search(db_session: Session, db_engine):
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx_user_data: dict = {}

    update = _fake_update(text="Thessaloniki")
    ctx = _fake_context(sf, ctx_user_data)
    next_state = await handle_location_text(update, ctx)
    assert next_state == PRICE_MIN
    assert ctx_user_data["location_slug"] == "ChIJ7eAoFPQ4qBQRqXTVuBXnugk"

    update = _fake_update(text="600")
    next_state = await handle_price_min(update, ctx)
    assert next_state == PRICE_MAX
    assert ctx_user_data["min_price"] == 600

    update = _fake_update(text="1200")
    next_state = await handle_price_max(update, ctx)
    assert next_state == BEDROOMS
    assert ctx_user_data["max_price"] == 1200

    update = _fake_update(text="2")
    end_state = await handle_bedrooms(update, ctx)
    assert end_state == -1  # ConversationHandler.END

    # Pull from a fresh session to verify persisted
    with sf() as verify_session:
        from home_scanner.db.repositories import get_or_create_user
        u = get_or_create_user(
            verify_session, telegram_chat_id=100, telegram_username="tester"
        )
        rows = list_user_saved_searches(verify_session, user_id=u.id)
        assert len(rows) == 1
        s = rows[0]
        assert s.location_slug == "ChIJ7eAoFPQ4qBQRqXTVuBXnugk"
        assert s.min_price == 600 and s.max_price == 1200
        assert s.min_bedrooms == 2 and s.max_bedrooms == 2
        verify_session.rollback()


@pytest.mark.asyncio
async def test_unknown_location_offers_close_matches(db_engine):
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx = _fake_context(sf, {})
    update = _fake_update(text="xyzzy nowhere")
    next_state = await handle_location_text(update, ctx)
    # Stays in LOCATION state, asks again
    assert next_state == LOCATION


@pytest.mark.asyncio
async def test_cold_start_digest_records_existing_matches(db_session: Session, db_engine):
    """Existing listings matching the new search are recorded into alerts_sent
    so the user isn't flooded on the next scrape."""
    from home_scanner.db.repositories import listing_ids_already_alerted, upsert_listing

    upsert_listing(
        db_session, now=datetime.now(UTC),
        external_id="cold-1", url="https://x", title=None,
        price_eur=900, bedrooms=2, area_m2=None, location_text=None,
    )
    db_session.commit()

    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx_user_data: dict = {}

    update = _fake_update(text="Thessaloniki")
    ctx = _fake_context(sf, ctx_user_data)
    await handle_location_text(update, ctx)
    await handle_price_min(_fake_update(text="skip"), ctx)
    await handle_price_max(_fake_update(text="skip"), ctx)
    await handle_bedrooms(_fake_update(text="2"), ctx)

    with sf() as v:
        from home_scanner.db.repositories import get_or_create_user, list_user_saved_searches
        u = get_or_create_user(v, telegram_chat_id=100, telegram_username="tester")
        searches = list_user_saved_searches(v, user_id=u.id)
        assert len(searches) == 1
        already = listing_ids_already_alerted(v, search_id=searches[0].id)
        assert len(already) == 1
        v.rollback()
