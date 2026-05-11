# home-scanner

Telegram alerts for new Greek apartment rentals on **xe.gr**. Scrapes hourly, alerts you when a listing matches your saved filters.

## Status

- **Plan 1 — Backend MVP** complete
- **Plan 2 — Production deploy** complete (FastAPI service, Dockerfile, Fly.io scale-to-zero, GitHub Actions hourly cron + CI + daily canary, Sentry wiring)
- **Plan 3 — Next.js frontend** upcoming

Originally targeted spitogatos.gr; pivoted to xe.gr after discovering Spitogatos uses an F5/Reese84 anti-bot WAF that serves stub HTML to non-browser clients. xe.gr ships clean server-rendered HTML to any client with no proxy or fingerprint trickery — same product story, simpler architecture.

See `docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md` for the design and `docs/superpowers/plans/` for the build plans.

## Local setup

Requirements: Python 3.12, Poetry, Docker (for local Postgres), a Telegram bot token from [@BotFather](https://t.me/botfather).

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
# Edit .env: fill DATABASE_URL, TELEGRAM_BOT_TOKEN. DataImpulse fields are
# optional — xe.gr doesn't need a proxy.

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

Requirements: a [Fly.io account](https://fly.io), `flyctl` installed, a [Neon](https://neon.tech) Postgres database (free tier), a [Sentry](https://sentry.io) project (optional).

### One-time setup

```bash
cd backend

# Create the Fly app
flyctl apps create home-scanner   # change name if collided

# Set secrets (the easy path is via the Fly web UI at
# https://fly.io/apps/<your-app>/secrets — adding each one at a time prevents
# multi-line paste mishaps).
flyctl secrets set \
  DATABASE_URL=postgresql+psycopg://USER:PASS@HOST/DB?sslmode=require \
  TELEGRAM_BOT_TOKEN=... \
  SCRAPE_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  TELEGRAM_WEBHOOK_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  SENTRY_DSN=... \
  PUBLIC_BASE_URL=https://home-scanner.fly.dev

# First deploy (release_command runs `alembic upgrade head`)
flyctl deploy

# Register the webhook URL with Telegram (one-shot, replace both vars)
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://home-scanner.fly.dev/webhook/telegram/${TELEGRAM_WEBHOOK_SECRET}"
```

**Important:** `DATABASE_URL` from Neon must use the `postgresql+psycopg://...` scheme (Neon's UI gives `postgresql://...`; prepend `+psycopg`). Without it, alembic fails at deploy.

### Subsequent deploys

```bash
cd backend && flyctl deploy
```

The release_command runs first; if migrations fail the deploy aborts and the previous version keeps serving.

### Verify

```bash
curl https://home-scanner.fly.dev/healthz
# → {"status": "down" or "ok", ...}

SCRAPE_SECRET='<your value>'
curl -H "Authorization: Bearer $SCRAPE_SECRET" -X POST https://home-scanner.fly.dev/internal/scrape
# → {"searches_processed": ..., "listings_seen": ..., ...}
```

### GitHub Actions secrets (required for cron + canary)

Add in repo Settings → Secrets and variables → Actions:

- `APP_URL` — public URL of the deployed app (e.g. `https://home-scanner.fly.dev`)
- `SCRAPE_SECRET` — same value used in `flyctl secrets set SCRAPE_SECRET=...`
- *(Optional — only if you re-enable DataImpulse proxying)* `DATAIMPULSE_USER`, `DATAIMPULSE_PASS`, `DATAIMPULSE_HOST`, `DATAIMPULSE_PORT` for the daily canary

Without `APP_URL` + `SCRAPE_SECRET` set, the hourly cron workflow still runs but the curl exits non-zero (visible in the Actions tab).

## Adding new locations

The bot's `/new` wizard matches against `backend/home_scanner/locations.yml`. Each entry maps a Greek city/area to xe.gr's Google Place ID. To add a new area:

1. Open https://www.xe.gr/property/results?item_type=re_residence&transaction_name=rent in your browser
2. Use xe.gr's location autocomplete to pick the area
3. Copy the `ChIJ...` value from the resulting URL's `geo_place_ids[]` parameter
4. Add an entry to `locations.yml`:
   ```yaml
   - name: "Your Area"
     aliases: ["alias1", "ελληνικά"]
     slug: "ChIJ..."
   ```
5. Commit, deploy.

## Architecture

See [`docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md`](docs/superpowers/specs/2026-05-08-home-scanner-portfolio-design.md).

## License

MIT — see `LICENSE`.
