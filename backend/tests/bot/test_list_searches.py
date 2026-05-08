from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session, sessionmaker

from home_scanner.bot.handlers.list_searches import list_searches
from home_scanner.db.repositories import create_saved_search, get_or_create_user


@pytest.mark.asyncio
async def test_list_shows_user_saved_searches(db_session: Session, db_engine):
    user = get_or_create_user(db_session, telegram_chat_id=200, telegram_username="me")
    create_saved_search(
        db_session, user_id=user.id,
        location_slug="marousi", min_price=600, max_price=1200,
        min_bedrooms=2, max_bedrooms=2,
    )
    create_saved_search(db_session, user_id=user.id, location_slug="kallithea")
    db_session.commit()

    update = MagicMock()
    update.effective_chat.id = 200
    update.effective_user.id = 200
    update.effective_user.username = "me"
    update.effective_message.reply_markdown_v2 = AsyncMock()

    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx = MagicMock()
    ctx.bot_data = {"session_factory": sf}

    await list_searches(update, ctx)

    body = update.effective_message.reply_markdown_v2.await_args.args[0]
    assert "marousi" in body.lower()
    assert "kallithea" in body.lower()


@pytest.mark.asyncio
async def test_list_empty(db_engine):
    update = MagicMock()
    update.effective_chat.id = 999
    update.effective_user.id = 999
    update.effective_user.username = None
    update.effective_message.reply_markdown_v2 = AsyncMock()

    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx = MagicMock()
    ctx.bot_data = {"session_factory": sf}

    await list_searches(update, ctx)
    body = update.effective_message.reply_markdown_v2.await_args.args[0]
    assert "no saved searches" in body.lower() or "create" in body.lower()
