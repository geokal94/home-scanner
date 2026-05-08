from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session, sessionmaker

from home_scanner.bot.handlers.manage import delete, pause, resume
from home_scanner.db.models import SavedSearch
from home_scanner.db.repositories import create_saved_search, get_or_create_user


def _ctx(args: list[str], db_engine):
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    ctx = MagicMock()
    ctx.bot_data = {"session_factory": sf}
    ctx.args = args
    return ctx


def _update(chat_id: int = 300):
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_user.id = chat_id
    update.effective_user.username = "u"
    update.effective_message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_pause_resume(db_session: Session, db_engine):
    user = get_or_create_user(db_session, telegram_chat_id=300, telegram_username="u")
    s = create_saved_search(db_session, user_id=user.id, location_slug="marousi")
    db_session.commit()

    await pause(_update(), _ctx([str(s.id)], db_engine))
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    with sf() as v:
        assert v.get(SavedSearch, s.id).is_active is False
        v.rollback()

    await resume(_update(), _ctx([str(s.id)], db_engine))
    with sf() as v:
        assert v.get(SavedSearch, s.id).is_active is True
        v.rollback()


@pytest.mark.asyncio
async def test_delete(db_session: Session, db_engine):
    user = get_or_create_user(db_session, telegram_chat_id=300, telegram_username="u")
    s = create_saved_search(db_session, user_id=user.id, location_slug="kallithea")
    db_session.commit()
    sid = s.id

    await delete(_update(), _ctx([str(sid)], db_engine))
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    with sf() as v:
        assert v.get(SavedSearch, sid) is None
        v.rollback()


@pytest.mark.asyncio
async def test_delete_other_users_search_refused(db_session: Session, db_engine):
    other = get_or_create_user(db_session, telegram_chat_id=999, telegram_username=None)
    s = create_saved_search(db_session, user_id=other.id, location_slug="x")
    db_session.commit()
    sid = s.id

    update = _update(chat_id=300)  # different user
    await delete(update, _ctx([str(sid)], db_engine))
    sf = sessionmaker(bind=db_engine, expire_on_commit=False)
    with sf() as v:
        assert v.get(SavedSearch, sid) is not None
        v.rollback()
    update.effective_message.reply_text.assert_awaited_with("No such saved search.")
