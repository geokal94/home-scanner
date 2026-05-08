"""/pause /resume /delete — manage existing saved searches by ID."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from home_scanner.db.models import SavedSearch
from home_scanner.db.repositories import (
    delete_saved_search,
    get_or_create_user,
    set_saved_search_active,
)


def _parse_id(args: list[str]) -> int | None:
    if not args:
        return None
    try:
        return int(args[0])
    except ValueError:
        return None


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle(update, context, is_active=False, verb="paused")


async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _toggle(update, context, is_active=True, verb="resumed")


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not (update.effective_message and update.effective_user):
        return
    search_id = _parse_id(context.args or [])
    if search_id is None:
        await update.effective_message.reply_text("Usage: /delete <id>")
        return
    sf = context.bot_data["session_factory"]
    with sf() as session:
        chat = update.effective_chat
        usr = update.effective_user
        u = get_or_create_user(
            session, telegram_chat_id=chat.id if chat else 0,
            telegram_username=usr.username,
        )
        s = session.get(SavedSearch, search_id)
        if s is None or s.user_id != u.id:
            session.commit()
            await update.effective_message.reply_text("No such saved search.")
            return
        delete_saved_search(session, search_id=search_id)
        session.commit()
    await update.effective_message.reply_text(f"Deleted #{search_id}.")


async def _toggle(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    is_active: bool,
    verb: str,
) -> None:
    if not (update.effective_message and update.effective_user):
        return
    search_id = _parse_id(context.args or [])
    if search_id is None:
        await update.effective_message.reply_text(f"Usage: /{verb[:-1]} <id>")
        return
    sf = context.bot_data["session_factory"]
    with sf() as session:
        chat = update.effective_chat
        usr = update.effective_user
        u = get_or_create_user(
            session, telegram_chat_id=chat.id if chat else 0,
            telegram_username=usr.username,
        )
        s = session.get(SavedSearch, search_id)
        if s is None or s.user_id != u.id:
            session.commit()
            await update.effective_message.reply_text("No such saved search.")
            return
        set_saved_search_active(session, search_id=search_id, is_active=is_active)
        session.commit()
    await update.effective_message.reply_text(f"#{search_id} {verb}.")
