"""telegram.ext.Application factories. Polling for local dev, webhook for prod."""
from __future__ import annotations

from sqlalchemy.orm import sessionmaker
from telegram.ext import Application, CommandHandler

from home_scanner.bot.handlers.list_searches import list_searches
from home_scanner.bot.handlers.manage import delete, pause, resume
from home_scanner.bot.handlers.new_search import build_handler as build_new_handler
from home_scanner.bot.handlers.start_help import help_cmd, start
from home_scanner.settings import Settings


def _register_handlers(app: Application, session_factory: sessionmaker) -> None:
    app.bot_data["session_factory"] = session_factory
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(build_new_handler())
    app.add_handler(CommandHandler("list", list_searches))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("delete", delete))


def build_application(*, session_factory: sessionmaker) -> Application:
    """Polling-mode Application — used by `python -m home_scanner bot` (local dev)."""
    settings = Settings()
    app = Application.builder().token(settings.telegram_bot_token).build()
    _register_handlers(app, session_factory)
    return app


async def build_webhook_application(*, session_factory: sessionmaker) -> Application:
    """Webhook-mode Application — initialized but NOT polling. The FastAPI
    /webhook/telegram/<secret> endpoint feeds it updates via app.process_update().

    Caller is responsible for `await app.initialize()` / `await app.shutdown()` —
    typically wired through FastAPI's lifespan."""
    settings = Settings()
    app = Application.builder().token(settings.telegram_bot_token).updater(None).build()
    _register_handlers(app, session_factory)
    return app
