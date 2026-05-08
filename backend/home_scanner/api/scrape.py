"""POST /internal/scrape — bearer-secret-authenticated trigger for one scrape cycle.

Called by the GitHub Actions cron workflow. Runs the same notifier.runner cycle
that `python -m home_scanner scrape` does, just over HTTP.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from home_scanner.api.deps import make_get_session, require_scrape_secret
from home_scanner.bot.app import build_application
from home_scanner.notifier.runner import run_one_scrape_cycle
from home_scanner.scraper import SpitogatosClient, scrape_search
from home_scanner.settings import Settings

log = structlog.get_logger(__name__)


def build_router(session_factory) -> APIRouter:  # type: ignore[no-untyped-def]
    get_session = make_get_session(session_factory)
    r = APIRouter()

    @r.post("/internal/scrape", dependencies=[Depends(require_scrape_secret)])
    async def trigger_scrape(session: Session = Depends(get_session)) -> dict[str, Any]:
        settings = Settings()
        app = build_application(session_factory=session_factory)
        client = SpitogatosClient(proxy_url=settings.proxy_url)

        summary = await run_one_scrape_cycle(
            session=session,
            bot=app.bot,
            scrape_search_fn=scrape_search,
            client=client,
            now=datetime.now(UTC),
        )
        session.commit()

        log.info(
            "api.scrape.done",
            searches=summary.searches_processed,
            listings=summary.listings_seen,
            alerts=summary.new_alerts,
        )

        return {
            "searches_processed": summary.searches_processed,
            "listings_seen": summary.listings_seen,
            "new_alerts": summary.new_alerts,
            "errors": summary.errors,
        }

    return r
