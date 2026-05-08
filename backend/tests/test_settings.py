import pytest

from home_scanner.settings import Settings


def test_loads_required_env_vars(monkeypatch):
    monkeypatch.setenv("DATAIMPULSE_USER", "u")
    monkeypatch.setenv("DATAIMPULSE_PASS", "p")
    monkeypatch.setenv("DATAIMPULSE_HOST", "gw.example.com")
    monkeypatch.setenv("DATAIMPULSE_PORT", "823")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@h:5432/db")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")

    s = Settings()

    assert s.dataimpulse_user == "u"
    assert s.proxy_url == "http://u:p@gw.example.com:823"
    assert s.database_url == "postgresql+psycopg://u:p@h:5432/db"
    assert s.telegram_bot_token == "t"
    assert s.log_level == "INFO"  # default


def test_raises_on_missing_required(monkeypatch):
    monkeypatch.delenv("DATAIMPULSE_USER", raising=False)
    with pytest.raises(KeyError):
        Settings()
