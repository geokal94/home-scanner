"""/new wizard: location → min price → max price → bedrooms → save.

Implemented as a ConversationHandler with explicit per-state handlers so each
state is unit-testable without spinning up the Application.
"""
from __future__ import annotations

from datetime import UTC, datetime

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from home_scanner.bot.messages import escape_md
from home_scanner.db.models import SavedSearch
from home_scanner.db.repositories import (
    create_saved_search,
    get_or_create_user,
    listings_matching_search,
    record_alert,
)
from home_scanner.locations import find_locations

LOCATION, PRICE_MIN, PRICE_MAX, BEDROOMS = range(4)


async def start_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    if update.effective_message:
        await update.effective_message.reply_markdown_v2(
            "Where? Type a city or Athens neighbourhood "
            "\\(e\\.g\\. *Marousi*, *Athens centre*, *Thessaloniki*\\)\\."
        )
    return LOCATION


async def handle_location_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip() if update.effective_message else ""
    matches = find_locations(text)
    if not matches:
        if update.effective_message:
            await update.effective_message.reply_text(
                "I don't recognise that area. Try a major Greek city or Athens neighbourhood."
            )
        return LOCATION
    chosen = matches[0]
    context.user_data["location_slug"] = chosen.slug
    context.user_data["location_name"] = chosen.name
    if update.effective_message:
        await update.effective_message.reply_text(
            f"Got it — {chosen.name}. Min monthly rent in € ('skip' for no minimum)?"
        )
    return PRICE_MIN


async def handle_price_min(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = _parse_int_or_skip(update.effective_message.text if update.effective_message else "")
    context.user_data["min_price"] = value
    if update.effective_message:
        await update.effective_message.reply_text("Max monthly rent in €?")
    return PRICE_MAX


async def handle_price_max(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    value = _parse_int_or_skip(update.effective_message.text if update.effective_message else "")
    context.user_data["max_price"] = value
    if update.effective_message:
        await update.effective_message.reply_text("Bedrooms? (Studio, 1, 2, 3, 4+, Any)")
    return BEDROOMS


async def handle_bedrooms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip().lower() if update.effective_message else ""
    min_br, max_br = _parse_bedrooms(text)

    sf = context.bot_data["session_factory"]

    # Step 1: Save the search
    with sf() as session:
        chat = update.effective_chat
        usr = update.effective_user
        u = get_or_create_user(
            session,
            telegram_chat_id=chat.id if chat else 0,
            telegram_username=usr.username if usr else None,
        )
        saved = create_saved_search(
            session,
            user_id=u.id,
            location_slug=context.user_data["location_slug"],
            name=context.user_data.get("location_name"),
            min_price=context.user_data.get("min_price"),
            max_price=context.user_data.get("max_price"),
            min_bedrooms=min_br,
            max_bedrooms=max_br,
        )
        session.commit()
        saved_id = saved.id

    # Step 2: Cold-start digest — seed alerts_sent with current matches, build sample
    with sf() as session:
        fresh = session.get(SavedSearch, saved_id)
        matches = list(listings_matching_search(session, search=fresh))
        now = datetime.now(UTC)
        for listing in matches:
            record_alert(
                session,
                saved_search_id=fresh.id,
                listing_id=listing.id,
                sent_at=now,
                telegram_message_id=None,  # not actually sent — just baseline
            )
        session.commit()
        match_count = len(matches)
        sample_text = "\n\n".join(
            f"€{m.price_eur:,} · {m.bedrooms or '—'} BR · {m.location_text or ''}"
            for m in matches[:3]
        )

    # Step 3: Reply
    if update.effective_message:
        loc_name = context.user_data.get("location_name", "")
        if match_count == 0:
            await update.effective_message.reply_markdown_v2(
                f"Saved ✓ Watching for new matches in *{escape_md(loc_name)}*\\.\n"
                f"_No current matches; you'll be pinged on new ones\\._"
            )
        else:
            await update.effective_message.reply_markdown_v2(
                f"Saved ✓ Watching *{escape_md(loc_name)}*\\.\n\n"
                f"Found *{match_count}* current matches — latest 3:\n\n{escape_md(sample_text)}\n\n"
                f"_New ones will arrive here as they appear\\._"
            )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_message:
        await update.effective_message.reply_text("OK, cancelled. Run /new when ready.")
    return ConversationHandler.END


def _parse_int_or_skip(text: str) -> int | None:
    text = text.strip().lower()
    if text in {"skip", "no", "none", "no min", "no max", ""}:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_bedrooms(text: str) -> tuple[int | None, int | None]:
    text = text.strip().lower()
    if text in {"any", ""}:
        return None, None
    if text == "studio":
        return 0, 0
    if text.endswith("+"):
        try:
            return int(text[:-1]), None
        except ValueError:
            return None, None
    try:
        n = int(text)
        return n, n
    except ValueError:
        return None, None


def build_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("new", start_new)],
        states={
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location_text)],
            PRICE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_min)],
            PRICE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_price_max)],
            BEDROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bedrooms)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        conversation_timeout=300,
    )
