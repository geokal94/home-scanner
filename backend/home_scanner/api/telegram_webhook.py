"""POST /webhook/telegram/<secret> — Telegram update webhook.

Telegram POSTs JSON-encoded Update objects to this URL. We dispatch them to the
shared `Application` instance which routes them to the registered handlers.

Auth: the secret is in the URL path (Telegram doesn't sign requests). Path is
non-guessable; verifying it matches the configured TELEGRAM_WEBHOOK_SECRET on
each request prevents replay from leaked URLs.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from telegram import Update
from telegram.ext import Application

from home_scanner.settings import Settings

log = structlog.get_logger(__name__)


def build_router(application: Application) -> APIRouter:
    r = APIRouter()

    @r.post("/webhook/telegram/{secret}")
    async def telegram_webhook(secret: str, request: Request) -> dict[str, str]:
        settings = Settings()
        if not settings.telegram_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook not configured",
            )
        if secret != settings.telegram_webhook_secret:
            log.warning("webhook.bad_secret")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        body = await request.json()
        try:
            update = Update.de_json(body, application.bot)
        except (TypeError, ValueError) as exc:
            # Malformed payload — log and 200 so Telegram doesn't retry.
            log.warning("webhook.unparseable_body", error=str(exc))
            return {"status": "ignored"}
        if update is None:
            return {"status": "ignored"}

        await application.process_update(update)
        return {"status": "ok"}

    return r
