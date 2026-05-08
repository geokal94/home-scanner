"""/list — show the user's saved searches."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from home_scanner.bot.messages import escape_md
from home_scanner.db.repositories import get_or_create_user, list_user_saved_searches


async def list_searches(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sf = context.bot_data["session_factory"]
    chat = update.effective_chat
    usr = update.effective_user
    if not (chat and usr and update.effective_message):
        return

    with sf() as session:
        u = get_or_create_user(
            session,
            telegram_chat_id=chat.id,
            telegram_username=usr.username,
        )
        rows = list_user_saved_searches(session, user_id=u.id)
        session.commit()

    if not rows:
        await update.effective_message.reply_markdown_v2(
            "You have no saved searches yet\\. Run /new to create one\\."
        )
        return

    lines = ["*Your saved searches*"]
    for s in rows:
        bounds = []
        if s.min_price is not None or s.max_price is not None:
            bounds.append(f"€{s.min_price or '-'}-{s.max_price or '-'}")
        if s.min_bedrooms is not None or s.max_bedrooms is not None:
            bounds.append(f"{s.min_bedrooms or '-'}-{s.max_bedrooms or '-'} BR")
        status = "active" if s.is_active else "paused"
        bounds_str = ", ".join(bounds) if bounds else "any"
        lines.append(
            f"`#{s.id}` {escape_md(s.location_slug)} \\({escape_md(bounds_str)}\\) — {status}"
        )
    lines.append("\nUse /pause `<id>`, /resume `<id>`, or /delete `<id>`\\.")
    await update.effective_message.reply_markdown_v2("\n".join(lines))
