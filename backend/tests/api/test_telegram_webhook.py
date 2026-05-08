from fastapi.testclient import TestClient


def test_webhook_requires_configured_secret(
    api_client: TestClient, monkeypatch
):
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    response = api_client.post("/webhook/telegram/anything", json={})
    assert response.status_code == 503


def test_webhook_rejects_wrong_secret(api_client: TestClient, monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "right-secret")
    response = api_client.post(
        "/webhook/telegram/wrong-secret", json={"update_id": 1}
    )
    assert response.status_code == 404


def test_webhook_accepts_valid_secret_with_unparseable_body(
    api_client: TestClient, monkeypatch
):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "right-secret")
    # Empty body → Update.de_json returns None → ignored without 500
    response = api_client.post(
        "/webhook/telegram/right-secret", json={}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
