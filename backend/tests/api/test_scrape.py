from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from home_scanner.db.repositories import create_saved_search, get_or_create_user
from home_scanner.scraper.models import ScrapedListing


def test_scrape_requires_authorization_header(api_client: TestClient, monkeypatch):
    monkeypatch.setenv("SCRAPE_SECRET", "test-secret")
    response = api_client.post("/internal/scrape")
    assert response.status_code == 401


def test_scrape_rejects_wrong_secret(api_client: TestClient, monkeypatch):
    monkeypatch.setenv("SCRAPE_SECRET", "test-secret")
    response = api_client.post(
        "/internal/scrape",
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401


def test_scrape_returns_503_when_no_secret_configured(
    api_client: TestClient, monkeypatch
):
    monkeypatch.delenv("SCRAPE_SECRET", raising=False)
    response = api_client.post(
        "/internal/scrape",
        headers={"Authorization": "Bearer anything"},
    )
    assert response.status_code == 503


def test_scrape_executes_cycle_with_valid_secret(
    api_client: TestClient,
    db_session: Session,
    session_factory: sessionmaker,
    monkeypatch,
):
    monkeypatch.setenv("SCRAPE_SECRET", "test-secret")
    user = get_or_create_user(db_session, telegram_chat_id=42, telegram_username=None)
    create_saved_search(db_session, user_id=user.id, location_slug="marousi")
    db_session.commit()

    fake_listings = [
        ScrapedListing(
            external_id="ext-1",
            url="https://x/1",
            title="t",
            price_eur=900,
            bedrooms=2,
            area_m2=60,
            location_text="Marousi",
        )
    ]

    with patch(
        "home_scanner.api.scrape.scrape_search", return_value=fake_listings
    ), patch("home_scanner.api.scrape.build_application") as mock_build:
        mock_app = mock_build.return_value
        mock_app.bot = AsyncMock()
        mock_app.bot.send_message.return_value.message_id = 1

        response = api_client.post(
            "/internal/scrape",
            headers={"Authorization": "Bearer test-secret"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["searches_processed"] == 1
    assert body["listings_seen"] == 1
    assert body["new_alerts"] == 1
