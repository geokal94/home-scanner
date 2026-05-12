# home-scanner

Telegram alerts for newly-posted apartment rentals on **xe.gr** (Greece's
largest classifieds site). Users configure saved searches in a Telegram bot;
an hourly scraper diffs new listings against ones they've already been
alerted about and pings them on Telegram within minutes of a match.

A small public website at [home-scanner.vercel.app](https://home-scanner.vercel.app)
shows the current listings inventory and links into the bot.

## Why this exists

xe.gr and other Greek rental sites are stateless — there's no "alert me when
a new 2BR in Athens centre under €1000 is posted." Greek renters check the
site every few hours; the good apartments are gone within 24h of being
listed. home-scanner closes that loop.

## Architecture

```
GitHub Actions (hourly cron)
        │ HTTP POST + bearer secret
        ▼
   ┌────────────────────────────┐         ┌─────────────────┐
   │  FastAPI on Fly.io         │ HTTPS   │  xe.gr          │
   │   • /healthz               │ ──────▶ │  (server-       │
   │   • /listings              │         │   rendered HTML)│
   │   • /internal/scrape       │         └─────────────────┘
   │   • /webhook/telegram      │
   │                            │ ◀────── Telegram webhook updates
   │  Modules:                  │
   │   • scraper  (httpx + bs4) │ ──────▶ Neon Postgres
   │   • notifier (diff+dispatch)│
   │   • bot      (python-PTB)  │ ──────▶ Telegram Bot API
   └────────────────────────────┘
            ▲  HTTPS (JSON)
            │
   ┌────────────────────────────┐
   │  Next.js on Vercel         │   ── consumed by browsers
   │   • /                      │
   │   • /listings(+ filters)   │
   │   • /listings/[slug]       │
   │   • /about                 │
   └────────────────────────────┘
```

**Backend** is a single Python service that boots an HTTP API, a long-polling-
or-webhook Telegram bot, and an on-demand scrape pipeline. It scales to zero
on Fly.io when idle (the GitHub Actions cron wakes it once an hour for the
scrape; Telegram webhooks wake it on user activity).

**Frontend** is a separate Next.js app that consumes the FastAPI JSON
endpoints. No Next.js API routes — clean consumer/server split.

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.12 (backend) + TypeScript (frontend) |
| Backend framework | FastAPI + `python-telegram-bot` |
| Database | Postgres 16 (Neon free tier in prod, testcontainers in CI) |
| ORM + migrations | SQLAlchemy 2 + Alembic |
| Scraper | `httpx` + `beautifulsoup4`, `tenacity` retry |
| Frontend framework | Next.js 16 (App Router) + Tailwind v4 |
| Package managers | Poetry (backend), pnpm (frontend) |
| Hosting | Fly.io (backend), Vercel (frontend), Neon (DB) |
| Observability | Sentry (optional), structlog |
| CI | GitHub Actions: hourly scrape cron, lint+test on PR, daily live-canary, Playwright smoke on Vercel deploy |
| Testing | pytest with real Postgres via testcontainers; Playwright E2E |

## Local setup

Requirements: Python 3.12, Poetry, Docker (for local Postgres + testcontainers),
a Telegram bot token from [@BotFather](https://t.me/botfather).

### Backend

```bash
cd backend
poetry install

# Start a local Postgres
docker run -d --name home_scanner_pg \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=home_scanner \
  -e POSTGRES_USER=home_scanner \
  -e POSTGRES_DB=home_scanner \
  postgres:16-alpine

cp .env.example .env  # then fill in DATABASE_URL + TELEGRAM_BOT_TOKEN

poetry run alembic upgrade head

# Three CLI entrypoints:
poetry run python -m home_scanner bot      # start the bot (long-polling)
poetry run python -m home_scanner scrape   # one scrape cycle, then exit
poetry run python -m home_scanner serve    # FastAPI server (production mode)
```

### Frontend

```bash
cd frontend
pnpm install
echo 'NEXT_PUBLIC_API_URL=http://localhost:8080' > .env.local
pnpm dev
```

Visit `http://localhost:3000`.

## Tests

```bash
cd backend && poetry run pytest -v
```

The suite spins up a real Postgres in a Docker testcontainer per session
(so Docker must be running). Tests cover the parser against saved xe.gr
HTML fixtures, the notifier's diff logic, Telegram message dispatch with
retry, the bot's `/new` conversation wizard, and the HTTP API.

```bash
cd frontend && pnpm test:e2e   # against a running dev server or PLAYWRIGHT_BASE_URL
```

## Design notes

- **`scraper.parser` is the only place that talks to xe.gr HTML.** When xe.gr
  changes its markup, the breakage is localised here. A daily
  `daily-canary.yml` workflow scrapes a known-busy URL and asserts ≥10
  listings parse; failure auto-opens a GitHub issue.
- **`notifier.diff` is a pure function with `Protocol`-typed inputs** — given
  saved searches + listings + the set of already-alerted IDs, returns which
  alerts to send. No DB, no Telegram, fully unit-tested.
- **Cold-start UX:** when a user creates a saved search, all currently-matching
  listings are seeded into `alerts_sent` immediately so the next scrape only
  pings about genuinely new listings, not the entire current inventory.
- **`/healthz` exposes `status: ok | degraded | down`** based on the most
  recent scrape run's age and status — the frontend uses this for a footer
  pill that turns yellow/red when the pipeline is unhealthy.

## Project history

The project originally targeted spitogatos.gr. After Plan 2's first
production scrape returned zero listings, investigation showed Spitogatos
serves an empty Vue shell to non-browser clients (F5/Reese84 WAF
fingerprinting). The codebase was pivoted to xe.gr, which serves
SSR HTML to any client. The `zero_listings_on_200` canary built into the
runner caught this within minutes of deploying. The design spec, the
implementation plans, and the pivot decision are all preserved in
`docs/superpowers/`.

## License

MIT — see `LICENSE`.
