# home-scanner

Telegram alerts for new Greek apartment rentals on **spitogatos.gr**. Scrapes hourly, alerts you when a listing matches your saved filters.

## Status

- **Plan 1 — Backend MVP** complete
- **Plan 2 — Production deploy** complete (FastAPI service, Dockerfile, Fly.io scale-to-zero, GitHub Actions hourly cron + CI + daily canary, Sentry wiring)
- **Plan 3 — Next.js frontend** upcoming

See `docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md` for the full design and `docs/superpowers/plans/` for the build plans.

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

## Deploy (Plan 2)

Requirements: a [Fly.io account](https://fly.io), `flyctl` installed, a [Neon](https://neon.tech) Postgres database (free tier), a [Sentry](https://sentry.io) project (optional), all credentials populated locally first per "Local setup".

### One-time setup

```bash
cd backend

# Create the Fly app
flyctl apps create home-scanner   # change name if collided

# Set secrets (these become env vars in the running container)
flyctl secrets set \
  DATAIMPULSE_USER=... \
  DATAIMPULSE_PASS=... \
  DATAIMPULSE_HOST=gw.dataimpulse.com \
  DATAIMPULSE_PORT=823 \
  DATABASE_URL=postgresql+psycopg://USER:PASS@HOST/DB \
  TELEGRAM_BOT_TOKEN=... \
  SCRAPE_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  TELEGRAM_WEBHOOK_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  SENTRY_DSN=... \
  PUBLIC_BASE_URL=https://home-scanner.fly.dev

# First deploy (will run alembic upgrade head as release_command)
flyctl deploy

# Register the webhook URL with Telegram (one-shot)
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://home-scanner.fly.dev/webhook/telegram/${TELEGRAM_WEBHOOK_SECRET}"
```

### Subsequent deploys

```bash
cd backend && flyctl deploy
```

The release_command (`alembic upgrade head`) runs first; if migrations fail the deploy is aborted and the previous version stays serving.

### Verify

```bash
curl https://home-scanner.fly.dev/healthz
# → {"status": "down" or "ok", ...}

curl -H "Authorization: Bearer $SCRAPE_SECRET" -X POST https://home-scanner.fly.dev/internal/scrape
# → {"searches_processed": 0, ...} on first run
```

### GitHub Actions secrets (for cron + CI — added in T8/T9)

In your repo's Settings → Secrets and variables → Actions, add:

- `APP_URL` — public URL of the deployed app (e.g. `https://home-scanner.fly.dev`)
- `SCRAPE_SECRET` — same value used in `flyctl secrets set SCRAPE_SECRET=...`
- `DATAIMPULSE_USER`, `DATAIMPULSE_PASS`, `DATAIMPULSE_HOST`, `DATAIMPULSE_PORT` — for the daily canary workflow

## Architecture

See [`docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md`](docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md).

## License

MIT — see `LICENSE`.
