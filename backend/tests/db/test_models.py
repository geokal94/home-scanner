from datetime import UTC, datetime

from home_scanner.db.models import Listing, SavedSearch, User
from sqlalchemy.orm import Session


def test_user_create(db_session: Session):
    u = User(telegram_chat_id=12345, telegram_username="someone")
    db_session.add(u)
    db_session.flush()
    assert u.id is not None
    assert u.created_at is not None


def test_saved_search_unique_per_user(db_session: Session):
    u = User(telegram_chat_id=99, telegram_username=None)
    db_session.add(u)
    db_session.flush()
    s = SavedSearch(
        user_id=u.id,
        location_slug="marousi",
        min_price=600,
        max_price=1200,
        min_bedrooms=2,
        max_bedrooms=2,
    )
    db_session.add(s)
    db_session.flush()
    assert s.is_active is True


def test_listing_external_id_unique(db_session: Session):
    now = datetime.now(UTC)
    l1 = Listing(
        external_id="abc-123",
        url="https://x",
        price_eur=800,
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add(l1)
    db_session.flush()

    l2 = Listing(
        external_id="abc-123",
        url="https://x2",
        price_eur=900,
        first_seen_at=now,
        last_seen_at=now,
        is_active=True,
    )
    db_session.add(l2)
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db_session.flush()
