import pytest

from home_scanner.settings import Settings


def test_loads_required_env_vars(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.delenv("DATAIMPULSE_USER", raising=False)

    s = Settings()

    assert s.database_url == "postgresql+psycopg://u:p@h:5432/db"
    assert s.telegram_bot_token == "t"
    assert s.log_level == "INFO"  # default
    assert s.proxy_url is None  # No DataImpulse configured → no proxy


def test_proxy_url_when_dataimpulse_configured(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("DATAIMPULSE_USER", "u")
    monkeypatch.setenv("DATAIMPULSE_PASS", "p")
    monkeypatch.setenv("DATAIMPULSE_HOST", "gw.example.com")
    monkeypatch.setenv("DATAIMPULSE_PORT", "823")

    s = Settings()

    assert s.proxy_url == "http://u:p@gw.example.com:823"


def test_proxy_url_partial_dataimpulse_returns_none(monkeypatch):
    """If only some DataImpulse fields are set, proxy_url is None — safer than
    sending malformed proxy strings to httpx."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("DATAIMPULSE_USER", "u")
    monkeypatch.delenv("DATAIMPULSE_PASS", raising=False)
    monkeypatch.delenv("DATAIMPULSE_HOST", raising=False)
    monkeypatch.delenv("DATAIMPULSE_PORT", raising=False)

    s = Settings()
    assert s.proxy_url is None


def test_raises_on_missing_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    with pytest.raises(KeyError):
        Settings()


def test_raises_on_missing_telegram_bot_token(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(KeyError):
        Settings()
