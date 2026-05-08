"""Top-level scrape cycle: per-search scrape → upsert listings → diff → dispatch.

This is the function called by the CLI in Plan 1, and by `/internal/scrape` in Plan 2.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable

import structlog
from sqlalchemy.orm import Session
from telegram import Bot

from home_scanner.db.models import ScrapeRun
from home_scanner.db.repositories import (
    list_active_saved_searches,
    listing_ids_already_alerted,
    listings_matching_search,
    upsert_listing,
)
from home_scanner.scraper import (
    ScrapeError,
    ScrapedListing,
    SearchFilter,
    SpitogatosClient,
)

from .diff import compute_alerts_to_send
from .dispatch import dispatch_alerts

log = structlog.get_logger(__name__)


@dataclass
class RunSummary:
    searches_processed: int = 0
    listings_seen: int = 0
    new_alerts: int = 0
    errors: dict[str, Any] = field(default_factory=lambda: {"failed": {}})


ScrapeFn = Callable[..., Iterable[ScrapedListing]]


async def run_one_scrape_cycle(
    *,
    session: Session,
    bot: Bot,
    scrape_search_fn: ScrapeFn,
    client: SpitogatosClient | None = None,
    now: datetime,
) -> RunSummary:
    summary = RunSummary()
    run = ScrapeRun(started_at=now, status="running")
    session.add(run)
    session.flush()

    searches = list_active_saved_searches(session)
    chat_id_for_search = {s.id: s.user.telegram_chat_id for s in searches}

    all_alerts: list[tuple[int, int]] = []

    for search in searches:
        summary.searches_processed += 1
        f = SearchFilter(
            location_slug=search.location_slug,
            min_price=search.min_price,
            max_price=search.max_price,
            min_bedrooms=search.min_bedrooms,
            max_bedrooms=search.max_bedrooms,
        )
        try:
            scraped = list(scrape_search_fn(f, client=client))
        except ScrapeError as exc:
            log.warning("runner.search_failed", slug=search.location_slug, error=str(exc))
            summary.errors["failed"][search.location_slug] = str(exc)
            continue

        summary.listings_seen += len(scraped)

        # Upsert listings, then re-query DB-side matches (handles previously-seen ones too)
        for s in scraped:
            upsert_listing(
                session, now=now,
                external_id=s.external_id, url=s.url, title=s.title,
                price_eur=s.price_eur, bedrooms=s.bedrooms,
                area_m2=s.area_m2, location_text=s.location_text,
            )
        session.flush()

        candidates = listings_matching_search(session, search=search)
        already = listing_ids_already_alerted(session, search_id=search.id)
        alerts = compute_alerts_to_send(
            search, candidates, already_alerted_listing_ids=already
        )
        all_alerts.extend(alerts)

    summary.new_alerts = await dispatch_alerts(
        session, bot=bot, alerts=all_alerts,
        chat_id_for_search=chat_id_for_search, now=now,
    )

    run.finished_at = now
    run.searches_processed = summary.searches_processed
    run.listings_seen = summary.listings_seen
    run.new_alerts = summary.new_alerts
    run.errors = summary.errors
    run.status = "ok"
    session.flush()

    log.info(
        "runner.done",
        searches=summary.searches_processed,
        listings=summary.listings_seen,
        alerts=summary.new_alerts,
        failed=list(summary.errors["failed"].keys()),
    )
    return summary
