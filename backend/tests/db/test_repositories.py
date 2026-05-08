from datetime import UTC, datetime

from home_scanner.db.models import Listing, User
from home_scanner.db.repositories import (
    create_saved_search,
    delete_saved_search,
    get_or_create_user,
    list_active_saved_searches,
    list_user_saved_searches,
    set_saved_search_active,
    upsert_listing,
)
from sqlalchemy.orm import Session


def test_get_or_create_user_idempotent(db_session: Session):
    u1 = get_or_create_user(db_session, telegram_chat_id=42, telegram_username="x")
    u2 = get_or_create_user(db_session, telegram_chat_id=42, telegram_username="y")
    assert u1.id == u2.id


def test_create_and_list_saved_searches(db_session: Session):
    u = get_or_create_user(db_session, telegram_chat_id=1, telegram_username=None)
    s = create_saved_search(
        db_session,
        user_id=u.id,
        location_slug="marousi",
        min_price=500,
        max_price=900,
        min_bedrooms=1,
        max_bedrooms=2,
    )
    db_session.flush()
    assert s.id is not None

    rows = list_user_saved_searches(db_session, user_id=u.id)
    assert len(rows) == 1
    assert rows[0].location_slug == "marousi"


def test_set_active_and_delete(db_session: Session):
    u = get_or_create_user(db_session, telegram_chat_id=2, telegram_username=None)
    s = create_saved_search(db_session, user_id=u.id, location_slug="marousi")
    db_session.flush()

    set_saved_search_active(db_session, search_id=s.id, is_active=False)
    db_session.flush()
    refreshed = db_session.get(type(s), s.id)
    assert refreshed.is_active is False

    delete_saved_search(db_session, search_id=s.id)
    db_session.flush()
    assert db_session.get(type(s), s.id) is None


def test_list_active_saved_searches_skips_inactive(db_session: Session):
    u = get_or_create_user(db_session, telegram_chat_id=3, telegram_username=None)
    s_a = create_saved_search(db_session, user_id=u.id, location_slug="a")
    s_b = create_saved_search(db_session, user_id=u.id, location_slug="b")
    db_session.flush()
    set_saved_search_active(db_session, search_id=s_b.id, is_active=False)
    db_session.flush()
    rows = list_active_saved_searches(db_session)
    slugs = [r.location_slug for r in rows]
    assert "a" in slugs and "b" not in slugs


def test_upsert_listing_inserts_then_updates(db_session: Session):
    now = datetime.now(UTC)
    listing_data = dict(
        external_id="ext-1",
        url="https://x",
        title="t",
        price_eur=800,
        bedrooms=2,
        area_m2=60,
        location_text="loc",
    )
    upsert_listing(db_session, now=now, **listing_data)
    db_session.flush()

    later = datetime.now(UTC)
    listing_data["price_eur"] = 750  # price drop
    upsert_listing(db_session, now=later, **listing_data)
    db_session.flush()

    rows = db_session.query(Listing).filter_by(external_id="ext-1").all()
    assert len(rows) == 1
    assert rows[0].price_eur == 750
    assert rows[0].last_seen_at == later
    assert rows[0].first_seen_at == now
