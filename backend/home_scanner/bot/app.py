"""telegram.ext.Application factory. Long-polling in Plan 1; webhook adapter in Plan 2."""
from __future__ import annotations

from sqlalchemy.orm import sessionmaker
from telegram.ext import Application, CommandHandler

from home_scanner.bot.handlers.list_searches import list_searches
from home_scanner.bot.handlers.manage import delete, pause, resume
from home_scanner.bot.handlers.new_search import build_handler as build_new_handler
from home_scanner.bot.handlers.start_help import help_cmd, start
from home_scanner.settings import Settings


def build_application(*, session_factory: sessionmaker) -> Application:
    settings = Settings()
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )
    # Stash the session factory in app.bot_data for handlers to grab
    app.bot_data["session_factory"] = session_factory

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(build_new_handler())
    app.add_handler(CommandHandler("list", list_searches))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("delete", delete))

    return app
