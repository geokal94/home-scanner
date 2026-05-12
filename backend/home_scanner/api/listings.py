"""GET /listings — paginated browse endpoint with filter query params.

Filters mirror the bot's saved-search dimensions: location_slug, price range,
bedroom range. Used by the Plan 3 React frontend.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from home_scanner.api.deps import make_get_session
from home_scanner.db.models import Listing


def build_router(session_factory) -> APIRouter:  # type: ignore[no-untyped-def]
    get_session = make_get_session(session_factory)
    r = APIRouter()

    @r.get("/listings")
    def get_listings(
        session: Session = Depends(get_session),
        location: Annotated[str | None, Query(max_length=100)] = None,
        price_min: Annotated[int | None, Query(ge=0)] = None,
        price_max: Annotated[int | None, Query(ge=0)] = None,
        bedrooms_min: Annotated[int | None, Query(ge=0, le=20)] = None,
        bedrooms_max: Annotated[int | None, Query(ge=0, le=20)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 24,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        # Note: location filtering on listings table is approximate (matches against
        # `location_text`). Spec acknowledges the per-area pages live in the frontend
        # build (Plan 3) and use the location_slug from `locations.yml`.
        q = select(Listing).where(Listing.is_active.is_(True))
        count_q = select(func.count(Listing.id)).where(Listing.is_active.is_(True))

        if location is not None:
            ilike = f"%{location}%"
            q = q.where(Listing.location_text.ilike(ilike))
            count_q = count_q.where(Listing.location_text.ilike(ilike))
        if price_min is not None:
            q = q.where(Listing.price_eur >= price_min)
            count_q = count_q.where(Listing.price_eur >= price_min)
        if price_max is not None:
            q = q.where(Listing.price_eur <= price_max)
            count_q = count_q.where(Listing.price_eur <= price_max)
        if bedrooms_min is not None:
            cond = (Listing.bedrooms.is_(None)) | (Listing.bedrooms >= bedrooms_min)
            q = q.where(cond)
            count_q = count_q.where(cond)
        if bedrooms_max is not None:
            cond = (Listing.bedrooms.is_(None)) | (Listing.bedrooms <= bedrooms_max)
            q = q.where(cond)
            count_q = count_q.where(cond)

        total = session.scalar(count_q) or 0
        rows = session.scalars(
            q.order_by(Listing.first_seen_at.desc()).limit(limit).offset(offset)
        ).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "listings": [_to_dict(row) for row in rows],
        }

    return r


def _to_dict(listing: Listing) -> dict[str, Any]:
    return {
        "id": listing.id,
        "external_id": listing.external_id,
        "url": listing.url,
        "title": listing.title,
        "price_eur": listing.price_eur,
        "bedrooms": listing.bedrooms,
        "area_m2": listing.area_m2,
        "location_text": listing.location_text,
        "image_url": listing.image_url,
        "first_seen_at": listing.first_seen_at.isoformat(),
        "last_seen_at": listing.last_seen_at.isoformat(),
    }
