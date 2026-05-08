"""CLI entrypoints. Run with `poetry run python -m home_scanner <command>`.

Subcommands:
- scrape: Run one full scrape cycle synchronously, then exit
- bot: Start the Telegram bot in long-polling mode (blocks)
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime

from home_scanner.bot.app import build_application
from home_scanner.db.session import make_engine, make_session_factory
from home_scanner.logging import configure as configure_logging
from home_scanner.logging import new_correlation_id
from home_scanner.notifier.runner import run_one_scrape_cycle
from home_scanner.scraper import SpitogatosClient, scrape_search
from home_scanner.settings import Settings


async def _scrape_once() -> None:
    settings = Settings()
    new_correlation_id()
    engine = make_engine(settings.database_url)
    sf = make_session_factory(engine)
    app = build_application(session_factory=sf)
    client = SpitogatosClient(proxy_url=settings.proxy_url)
    with sf() as session:
        await run_one_scrape_cycle(
            session=session,
            bot=app.bot,
            scrape_search_fn=scrape_search,
            client=client,
            now=datetime.now(UTC),
        )
        session.commit()


def _run_bot() -> None:
    settings = Settings()
    engine = make_engine(settings.database_url)
    sf = make_session_factory(engine)
    app = build_application(session_factory=sf)
    app.run_polling()


def main() -> None:
    parser = argparse.ArgumentParser(prog="home-scanner")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scrape", help="Run one scrape cycle, then exit")
    sub.add_parser("bot", help="Run the Telegram bot in long-polling mode")
    args = parser.parse_args()

    configure_logging(Settings().log_level)

    if args.cmd == "scrape":
        asyncio.run(_scrape_once())
    elif args.cmd == "bot":
        _run_bot()


if __name__ == "__main__":
    main()
