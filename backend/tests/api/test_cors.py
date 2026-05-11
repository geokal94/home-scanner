from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker


def test_cors_allows_configured_origin(session_factory: sessionmaker, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://home-scanner.vercel.app")
    from home_scanner.api import build_app
    app = build_app(session_factory=session_factory)
    with TestClient(app) as client:
        response = client.options(
            "/listings",
            headers={
                "Origin": "https://home-scanner.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://home-scanner.vercel.app"


def test_cors_rejects_unknown_origin(session_factory: sessionmaker, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://home-scanner.vercel.app")
    from home_scanner.api import build_app
    app = build_app(session_factory=session_factory)
    with TestClient(app) as client:
        response = client.options(
            "/listings",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
    # CORS middleware doesn't set the Allow-Origin header → browser rejects
    assert "access-control-allow-origin" not in response.headers


def test_cors_disabled_when_no_origins_configured(
    session_factory: sessionmaker, monkeypatch
):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    from home_scanner.api import build_app
    app = build_app(session_factory=session_factory)
    with TestClient(app) as client:
        response = client.options(
            "/listings",
            headers={
                "Origin": "https://home-scanner.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
    # No middleware → preflight not handled → no allow header
    assert "access-control-allow-origin" not in response.headers
