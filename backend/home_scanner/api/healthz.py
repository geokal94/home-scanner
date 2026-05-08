"""GET /healthz — last scrape, status, listing counts. Used by uptime monitors
and the public landing page's freshness pill (Plan 3 frontend)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from home_scanner.api.deps import make_get_session
from home_scanner.db.models import Listing, ScrapeRun


def build_router(session_factory) -> APIRouter:  # type: ignore[no-untyped-def]
    get_session = make_get_session(session_factory)
    r = APIRouter()

    @r.get("/healthz")
    def healthz(session: Session = Depends(get_session)) -> dict[str, Any]:  # noqa: B008
        last_run = session.scalar(
            select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(1)
        )
        active_count = session.scalar(
            select(func.count(Listing.id)).where(Listing.is_active.is_(True))
        ) or 0

        if last_run is None:
            return {
                "status": "down",
                "last_scrape": None,
                "active_listings": active_count,
            }

        now = datetime.now(UTC)
        minutes_ago = int((now - last_run.started_at).total_seconds() / 60)

        if last_run.status == "failed":
            status_str = "down"
        elif minutes_ago > 90:
            status_str = "degraded"
        else:
            status_str = "ok"

        return {
            "status": status_str,
            "last_scrape": {
                "started_at": last_run.started_at.isoformat(),
                "status": last_run.status,
                "minutes_ago": minutes_ago,
            },
            "active_listings": active_count,
        }

    return r
