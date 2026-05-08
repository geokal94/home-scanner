from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from home_scanner.db.models import Listing, ScrapeRun


def test_healthz_with_no_scrape_runs(
    api_client: TestClient, db_session: Session
):
    response = api_client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "down"
    assert body["last_scrape"] is None
    assert body["active_listings"] == 0


def test_healthz_recent_ok_run(
    api_client: TestClient,
    session_factory: sessionmaker,
    db_session: Session,
):
    with session_factory() as s:
        s.add(ScrapeRun(
            started_at=datetime.now(UTC) - timedelta(minutes=15),
            finished_at=datetime.now(UTC) - timedelta(minutes=14),
            status="ok",
            errors={"failed": {}},
        ))
        s.commit()

    response = api_client.get("/healthz")
    body = response.json()
    assert body["status"] == "ok"
    assert body["last_scrape"]["status"] == "ok"
    assert 10 <= body["last_scrape"]["minutes_ago"] <= 20


def test_healthz_stale_run_is_degraded(
    api_client: TestClient,
    session_factory: sessionmaker,
):
    with session_factory() as s:
        s.add(ScrapeRun(
            started_at=datetime.now(UTC) - timedelta(minutes=120),
            status="ok",
            errors={"failed": {}},
        ))
        s.commit()

    response = api_client.get("/healthz")
    assert response.json()["status"] == "degraded"


def test_healthz_failed_run_is_down(
    api_client: TestClient,
    session_factory: sessionmaker,
):
    with session_factory() as s:
        s.add(ScrapeRun(
            started_at=datetime.now(UTC) - timedelta(minutes=15),
            status="failed",
            errors={"failed": {"all": "bot_detection"}},
        ))
        s.commit()

    response = api_client.get("/healthz")
    assert response.json()["status"] == "down"


def test_healthz_counts_active_listings(
    api_client: TestClient,
    session_factory: sessionmaker,
):
    now = datetime.now(UTC)
    with session_factory() as s:
        s.add(Listing(
            external_id="a", url="https://x", price_eur=800,
            first_seen_at=now, last_seen_at=now, is_active=True,
        ))
        s.add(Listing(
            external_id="b", url="https://y", price_eur=900,
            first_seen_at=now, last_seen_at=now, is_active=False,
        ))
        s.commit()

    response = api_client.get("/healthz")
    assert response.json()["active_listings"] == 1
