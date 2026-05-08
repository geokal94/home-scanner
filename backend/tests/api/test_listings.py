from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from home_scanner.db.models import Listing


def _make_listing(
    external_id: str,
    *,
    price: int = 800,
    bedrooms: int | None = 2,
    location: str | None = "Athens",
    is_active: bool = True,
    first_seen_at: datetime | None = None,
) -> Listing:
    now = datetime.now(UTC)
    return Listing(
        external_id=external_id,
        url=f"https://x/{external_id}",
        title=f"Listing {external_id}",
        price_eur=price,
        bedrooms=bedrooms,
        area_m2=60,
        location_text=location,
        first_seen_at=first_seen_at or now,
        last_seen_at=now,
        is_active=is_active,
    )


def test_listings_empty_returns_zero_total(
    api_client: TestClient, db_session: Session
):
    # `db_session` truncates at teardown, so a previous test's leftover rows may
    # still be present here. Clear `listings` up-front to assert the empty case.
    db_session.query(Listing).delete()
    db_session.commit()

    response = api_client.get("/listings")
    assert response.status_code == 200
    body = response.json()
    assert body == {"total": 0, "limit": 24, "offset": 0, "listings": []}


def test_listings_returns_active_only(
    api_client: TestClient, session_factory: sessionmaker, db_session: Session
):
    with session_factory() as s:
        s.add(_make_listing("a", is_active=True))
        s.add(_make_listing("b", is_active=False))
        s.commit()

    body = api_client.get("/listings").json()
    assert body["total"] == 1
    assert body["listings"][0]["external_id"] == "a"


def test_listings_price_filter(
    api_client: TestClient, session_factory: sessionmaker, db_session: Session
):
    with session_factory() as s:
        s.add(_make_listing("cheap", price=500))
        s.add(_make_listing("mid", price=800))
        s.add(_make_listing("expensive", price=1500))
        s.commit()

    body = api_client.get("/listings?price_min=600&price_max=1000").json()
    ids = sorted(item["external_id"] for item in body["listings"])
    assert ids == ["mid"]


def test_listings_bedrooms_filter_keeps_null(
    api_client: TestClient, session_factory: sessionmaker, db_session: Session
):
    with session_factory() as s:
        s.add(_make_listing("br2", bedrooms=2))
        s.add(_make_listing("br_null", bedrooms=None))
        s.add(_make_listing("br1", bedrooms=1))
        s.commit()

    body = api_client.get("/listings?bedrooms_min=2").json()
    ids = sorted(item["external_id"] for item in body["listings"])
    assert ids == ["br2", "br_null"]


def test_listings_location_substring(
    api_client: TestClient, session_factory: sessionmaker, db_session: Session
):
    with session_factory() as s:
        s.add(_make_listing("a", location="Athens Centre"))
        s.add(_make_listing("b", location="Marousi"))
        s.add(_make_listing("c", location="Athens, Pagrati"))
        s.commit()

    body = api_client.get("/listings?location=Athens").json()
    ids = sorted(item["external_id"] for item in body["listings"])
    assert ids == ["a", "c"]


def test_listings_pagination(
    api_client: TestClient, session_factory: sessionmaker, db_session: Session
):
    base = datetime.now(UTC)
    with session_factory() as s:
        for i in range(5):
            s.add(_make_listing(
                f"l{i}", price=800 + i,
                first_seen_at=base - timedelta(minutes=i),
            ))
        s.commit()

    body = api_client.get("/listings?limit=2&offset=0").json()
    assert body["total"] == 5
    assert len(body["listings"]) == 2
    # Ordered by first_seen_at desc → newest is l0
    assert body["listings"][0]["external_id"] == "l0"

    body2 = api_client.get("/listings?limit=2&offset=2").json()
    assert body2["listings"][0]["external_id"] == "l2"


def test_listings_invalid_query_param_rejected(api_client: TestClient):
    # bedrooms_max above 20 should 422 from FastAPI's validation
    response = api_client.get("/listings?bedrooms_max=99")
    assert response.status_code == 422
