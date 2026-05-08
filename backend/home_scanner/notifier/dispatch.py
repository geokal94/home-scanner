"""Send Telegram alert messages, record `alerts_sent` rows. Side-effecting."""
from __future__ import annotations

from datetime import datetime
from typing import Mapping

import structlog
from sqlalchemy.orm import Session
from telegram import Bot
from telegram.error import Forbidden, TelegramError
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from home_scanner.bot.messages import format_listing_alert
from home_scanner.db.models import Listing, SavedSearch
from home_scanner.db.repositories import deactivate_user, record_alert

log = structlog.get_logger(__name__)


async def dispatch_alerts(
    session: Session,
    *,
    bot: Bot,
    alerts: list[tuple[int, int]],
    chat_id_for_search: Mapping[int, int],
    now: datetime,
) -> int:
    """Send a Telegram message per (search_id, listing_id) tuple. Returns count sent."""
    sent = 0
    for search_id, listing_id in alerts:
        chat_id = chat_id_for_search.get(search_id)
        if chat_id is None:
            log.warning("dispatch.chat_id_missing", search_id=search_id)
            continue
        listing = session.get(Listing, listing_id)
        if listing is None:
            continue
        try:
            message = await _send_with_retry(bot, chat_id, listing)
        except Forbidden:
            log.info("dispatch.user_blocked_bot", chat_id=chat_id)
            search = session.get(SavedSearch, search_id)
            if search is not None:
                deactivate_user(session, user_id=search.user_id, at=now)
                session.flush()
            continue
        except (TelegramError, RetryError) as exc:
            log.error("dispatch.telegram_error", error=str(exc), chat_id=chat_id)
            continue

        record_alert(
            session,
            saved_search_id=search_id,
            listing_id=listing_id,
            sent_at=now,
            telegram_message_id=message.message_id if message else None,
        )
        session.flush()
        sent += 1
    return sent


async def _send_with_retry(bot: Bot, chat_id: int, listing: Listing):
    text = format_listing_alert(
        price_eur=listing.price_eur,
        bedrooms=listing.bedrooms,
        area_m2=listing.area_m2,
        location_text=listing.location_text,
        url=listing.url,
    )
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(TelegramError)
        & retry_if_not_exception_type(Forbidden),
        reraise=True,
    ):
        with attempt:
            return await bot.send_message(
                chat_id=chat_id, text=text, parse_mode="MarkdownV2"
            )
