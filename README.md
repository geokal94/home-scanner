# home-scanner

Telegram alerts for new Greek apartment rentals on **spitogatos.gr**. Scrapes hourly, alerts you when a listing matches your saved filters.

## Status

Backend MVP complete (see [`docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md`](docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md) for the full design and [`docs/superpowers/plans/2026-05-08-backend-mvp.md`](docs/superpowers/plans/2026-05-08-backend-mvp.md) for the build plan).

Plan 2 (production deploy) and Plan 3 (Next.js frontend) are upcoming.

## Local setup

Requirements: Python 3.12, Poetry, Docker (for local Postgres), a [DataImpulse](https://dataimpulse.com) proxy account, a Telegram bot token from [@BotFather](https://t.me/botfather).

```bash
# 1. Install Python deps
cd backend
poetry install

# 2. Start a local Postgres
docker run -d --name home_scanner_pg \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=home_scanner \
  -e POSTGRES_USER=home_scanner \
  -e POSTGRES_DB=home_scanner \
  postgres:16-alpine

# 3. Configure secrets
cp .env.example .env
# Edit .env: fill DATAIMPULSE_*, TELEGRAM_BOT_TOKEN

# 4. Apply migrations
poetry run alembic upgrade head
```

## Running

```bash
# Start the bot (long-polling — blocks the terminal)
poetry run python -m home_scanner bot

# In another terminal: trigger one scrape cycle
poetry run python -m home_scanner scrape
```

## End-to-end smoke test

1. Start the bot: `python -m home_scanner bot`
2. In Telegram: open your bot, send `/start`, then `/new`, follow the wizard.
3. Confirm a saved search appears via `/list`.
4. Stop the bot, then run: `python -m home_scanner scrape`
5. Confirm Telegram messages arrive for matching listings.

## Tests

```bash
poetry run pytest -v
```

The test suite spins up a real Postgres in a testcontainer, so Docker must be running.

## Architecture

See [`docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md`](docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md).

## License

MIT — see `LICENSE`.
