"""CRUD helpers used by the bot and notifier modules.

Functions take an explicit `Session` and never commit — the caller is responsible
for transaction lifecycle. This keeps tests transactional and the runtime free
to batch.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .models import AlertSent, Listing, SavedSearch, User

# --- users ---

def get_or_create_user(
    session: Session, *, telegram_chat_id: int, telegram_username: str | None
) -> User:
    existing = session.scalar(
        select(User).where(User.telegram_chat_id == telegram_chat_id)
    )
    if existing is not None:
        if telegram_username and existing.telegram_username != telegram_username:
            existing.telegram_username = telegram_username
        return existing
    new = User(
        telegram_chat_id=telegram_chat_id,
        telegram_username=telegram_username,
    )
    session.add(new)
    session.flush()
    return new


def deactivate_user(session: Session, *, user_id: int, at: datetime) -> None:
    user = session.get(User, user_id)
    if user is not None:
        user.deactivated_at = at


# --- saved searches ---

def create_saved_search(
    session: Session,
    *,
    user_id: int,
    location_slug: str,
    name: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_bedrooms: int | None = None,
    max_bedrooms: int | None = None,
) -> SavedSearch:
    s = SavedSearch(
        user_id=user_id,
        location_slug=location_slug,
        name=name,
        min_price=min_price,
        max_price=max_price,
        min_bedrooms=min_bedrooms,
        max_bedrooms=max_bedrooms,
    )
    session.add(s)
    session.flush()
    return s


def list_user_saved_searches(
    session: Session, *, user_id: int
) -> Sequence[SavedSearch]:
    return session.scalars(
        select(SavedSearch).where(SavedSearch.user_id == user_id).order_by(SavedSearch.id)
    ).all()


def list_active_saved_searches(session: Session) -> Sequence[SavedSearch]:
    return session.scalars(
        select(SavedSearch)
        .join(User, User.id == SavedSearch.user_id)
        .where(SavedSearch.is_active.is_(True))
        .where(User.deactivated_at.is_(None))
    ).all()


def set_saved_search_active(
    session: Session, *, search_id: int, is_active: bool
) -> None:
    s = session.get(SavedSearch, search_id)
    if s is not None:
        s.is_active = is_active


def delete_saved_search(session: Session, *, search_id: int) -> None:
    s = session.get(SavedSearch, search_id)
    if s is not None:
        session.delete(s)


# --- listings ---

def upsert_listing(
    session: Session,
    *,
    now: datetime,
    external_id: str,
    url: str,
    title: str | None,
    price_eur: int,
    bedrooms: int | None,
    area_m2: int | None,
    location_text: str | None,
    image_url: str | None = None,
) -> Listing:
    """Insert or update by external_id. Sets first_seen_at on insert, last_seen_at always."""
    stmt = insert(Listing).values(
        external_id=external_id,
        url=url,
        title=title,
        price_eur=price_eur,
        bedrooms=bedrooms,
        area_m2=area_m2,
        location_text=location_text,
        image_url=image_url,
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
    ).on_conflict_do_update(
        index_elements=[Listing.external_id],
        set_={
            "url": url,
            "title": title,
            "price_eur": price_eur,
            "bedrooms": bedrooms,
            "area_m2": area_m2,
            "location_text": location_text,
            "image_url": image_url,
            "last_seen_at": now,
            "is_active": True,
        },
    )
    session.execute(stmt)
    return session.scalar(select(Listing).where(Listing.external_id == external_id))  # type: ignore[return-value]


def listings_matching_search(
    session: Session, *, search: SavedSearch
) -> Sequence[Listing]:
    """Active listings whose price/bedrooms fall within the saved search's bounds."""
    q = select(Listing).where(Listing.is_active.is_(True))
    if search.min_price is not None:
        q = q.where(Listing.price_eur >= search.min_price)
    if search.max_price is not None:
        q = q.where(Listing.price_eur <= search.max_price)
    if search.min_bedrooms is not None:
        q = q.where(
            (Listing.bedrooms.is_(None)) | (Listing.bedrooms >= search.min_bedrooms)
        )
    if search.max_bedrooms is not None:
        q = q.where(
            (Listing.bedrooms.is_(None)) | (Listing.bedrooms <= search.max_bedrooms)
        )
    return session.scalars(q.order_by(Listing.first_seen_at.desc())).all()


# --- alerts_sent ---

def listing_ids_already_alerted(
    session: Session, *, search_id: int
) -> set[int]:
    return set(
        session.scalars(
            select(AlertSent.listing_id).where(AlertSent.saved_search_id == search_id)
        ).all()
    )


def record_alert(
    session: Session,
    *,
    saved_search_id: int,
    listing_id: int,
    sent_at: datetime,
    telegram_message_id: int | None = None,
) -> None:
    a = AlertSent(
        saved_search_id=saved_search_id,
        listing_id=listing_id,
        sent_at=sent_at,
        telegram_message_id=telegram_message_id,
    )
    session.add(a)
