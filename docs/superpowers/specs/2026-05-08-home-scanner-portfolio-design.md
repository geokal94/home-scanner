# home-scanner — Portfolio Project Design

**Date:** 2026-05-08
**Status:** Approved (brainstorming complete)
**Next step:** implementation plan via `superpowers:writing-plans`

---

## 1. Goal

Turn the existing single-file Spitogatos scraper into a portfolio project that is **both useful** (real apartment hunters in Greece can use it) **and impressive** (engineering quality and architecture stand up to recruiter / engineering review).

The hook: **smart alerts on newly-posted Spitogatos rentals via Telegram bot**. Source sites are stateless — refreshing manually is the only way to "be there first" today. We solve that.

## 2. Audience and success criteria

- **Primary audience:** Greek apartment hunters (real users) AND technical reviewers (recruiters, hiring managers).
- **Success looks like:**
  - A clickable live demo that doesn't 500 when a recruiter opens it.
  - A README that explains the architecture in 90 seconds.
  - Clean atomic git history showing deliberate engineering decisions.
  - At least a few real users using the bot.

## 3. Product shape

Two surfaces:

- **Telegram bot** (`@home_scanner_gr_bot`) — primary product. Users configure saved searches and receive alerts here. Identity = Telegram chat ID; no email, no password.
- **Web app** — public landing page + read-only browse view of currently-active listings. No filter/alert config (that lives in the bot). Serves as the portfolio frontend showcase and a discoverability surface.

### Scope decisions

| Decision | Choice | Why |
|---|---|---|
| Source | spitogatos.gr only | Single-source MVP; multi-source is a clean v2 extension. |
| Geography | All of Greece | Filterable per saved search; not Athens-only. |
| Listing type | Rentals only | "Be there first" is meaningful for rentals; weak for sales. |
| Filter dimensions | location, price (min/max), bedrooms (min/max) | Covers ~90% of search intent; smallest bot command surface. |
| Alert cadence | Hourly | Cost-efficient via DataImpulse; configurable in code for later tuning. |
| Cost target | ~$1/month | Scale-to-zero architecture; portfolio-first weighting. |

## 4. Architecture

**Approach: modest monolith, scale-to-zero variant.**

One Python service idle by default; runs only when invoked (Telegram message, web fetch, or GitHub Actions cron ping).

### Components

```
┌──────────────┐                  ┌────────────────────┐
│  GitHub      │ hourly POST →    │   Fly.io machine   │ ──► DataImpulse ──► spitogatos.gr
│  Actions     │ /internal/scrape │   (auto-stop on    │
│  Cron        │                  │    idle)           │
└──────────────┘                  │                    │
                                  │  • FastAPI         │
┌──────────────┐  webhook POST →  │  • Telegram bot    │
│  Telegram    │                  │  • Notifier        │
│  servers     │                  │  • Scraper         │
└──────────────┘                  └─────────┬──────────┘
                                            │
                                  ┌─────────▼──────────┐
┌──────────────┐  HTTPS →         │   Neon Postgres    │
│  Vercel      │ ◄── JSON ──      │   (auto-pause)     │
│  (Next.js)   │                  └────────────────────┘
└──────────────┘
       ▲
       │
   end users
```

### Modules (one Python package, `home_scanner.*`)

| Module | Responsibility | Dependencies |
|---|---|---|
| `scraper` | Fetch + parse Spitogatos rental search pages. Pure functions. | `requests`, `beautifulsoup4` |
| `db` | SQLAlchemy models, Alembic migrations, query helpers. | `sqlalchemy`, `alembic`, `psycopg` |
| `bot` | Telegram webhook handlers (`/new`, `/list`, `/delete`, `/pause`, `/resume`, `/help`). | `python-telegram-bot` |
| `api` | FastAPI: public `GET /listings`, `GET /healthz`; internal `POST /webhook/telegram/<secret>`, `POST /internal/scrape`. | `fastapi`, `uvicorn` |
| `notifier` | Reactive: invoked by `/internal/scrape` → iterate active saved_searches → scrape → diff → dispatch Telegram messages. No scheduler in-process. | `httpx` |

### Scheduling — externalised

`.github/workflows/scrape.yml` runs `cron: '0 * * * *'` and POSTs to `$APP_URL/internal/scrape` with a shared bearer secret. This is the *only* cron in the system. Lets the Fly machine sleep entirely between scrapes.

### Deploy targets

- **Backend:** Fly.io, `auto_stop_machines=true`, `min_machines_running=0`. Cold start ~1s.
- **Frontend:** Vercel hobby, separate `frontend/` directory. Calls FastAPI by URL via env var.
- **Database:** Neon Postgres free tier (auto-pauses; matches the scale-to-zero model).
- **Cron:** GitHub Actions on this repo.
- **Secrets:** Fly secrets + Vercel env vars. The current `config.py` pattern is retired.

### Operational costs

Target: ~$1/month all-in. Portfolio-first weighting drove the scale-to-zero choice.

| Component | Provider | Monthly cost |
|---|---|---|
| Backend | Fly.io shared-cpu-1x, scale-to-zero | ~$0 (idle most of the time, billed per second when awake) |
| Database | Neon Postgres free tier | $0 |
| Frontend | Vercel hobby | $0 |
| Proxy bandwidth | DataImpulse pay-as-you-go (~$1/GB) | ~$0.25–1 (1 search × hourly × ~50KB ≈ 36MB/month) |
| Telegram Bot API | — | $0 |
| GitHub Actions cron + CI | Public repo | $0 |
| **Total** | | **~$1/month** |

Vendor change risk is the hidden cost: free-tier policies tighten roughly every ~2 years (Heroku, Render, Fly all killed free tiers historically). Re-platforming budget: ~1 day every 2 years.

### Repo layout

Single repo, two top-level workspaces:

```
home-scanner/
├── backend/         (Python package, FastAPI + bot + scraper)
├── frontend/        (Next.js + Tailwind)
├── .github/workflows/
│   ├── ci.yml
│   ├── scrape.yml
│   └── daily-canary.yml
├── docs/superpowers/specs/
└── README.md
```

## 5. Data model

Postgres + SQLAlchemy + Alembic migrations. All timestamps `timestamptz`.

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | `bigint PK` | |
| `telegram_chat_id` | `bigint UNIQUE NOT NULL` | The identity. |
| `telegram_username` | `text` | Display only; nullable. |
| `deactivated_at` | `timestamptz` | Set when bot is blocked by user. |
| `created_at` | `timestamptz NOT NULL` | |

### `saved_searches`

| Column | Type | Notes |
|---|---|---|
| `id` | `bigint PK` | |
| `user_id` | `bigint FK → users` | |
| `name` | `text` | Human label. |
| `location_slug` | `text NOT NULL` | From `locations.yml`. |
| `min_price`, `max_price` | `int` | Euros, nullable for "no bound". |
| `min_bedrooms`, `max_bedrooms` | `smallint` | Nullable. |
| `is_active` | `bool NOT NULL DEFAULT true` | Soft pause. |
| `created_at`, `updated_at` | `timestamptz NOT NULL` | |

### `listings`

| Column | Type | Notes |
|---|---|---|
| `id` | `bigint PK` | |
| `external_id` | `text UNIQUE NOT NULL` | Spitogatos's stable listing ID — the dedup key. |
| `url` | `text NOT NULL` | |
| `title` | `text` | |
| `price_eur` | `int NOT NULL` | |
| `bedrooms` | `smallint` | Nullable — sometimes missing on the card. |
| `area_m2` | `smallint` | Nullable. |
| `location_text` | `text` | Raw location string. |
| `first_seen_at` | `timestamptz NOT NULL` | |
| `last_seen_at` | `timestamptz NOT NULL` | Updated on every scrape that still finds it. |
| `is_active` | `bool NOT NULL` | Set false when scrape no longer returns it. |

Index: `(price_eur, bedrooms)` for the public web app's filter queries.

### `alerts_sent`

| Column | Type | Notes |
|---|---|---|
| `saved_search_id` | `bigint FK` | Composite PK with `listing_id`. |
| `listing_id` | `bigint FK` | |
| `sent_at` | `timestamptz NOT NULL` | Written AFTER successful Telegram send. |
| `telegram_message_id` | `bigint` | Nullable; for future "edit on price drop". |

### `scrape_runs`

| Column | Type | Notes |
|---|---|---|
| `id` | `bigint PK` | |
| `started_at`, `finished_at` | `timestamptz` | |
| `status` | `text` | `running` / `ok` / `failed`. |
| `searches_processed`, `listings_seen`, `new_alerts` | `int` | |
| `errors` | `jsonb` | Per-search failures, shape: `{"failed": {"<location_slug>": "<short_reason>"}}`. Empty `{}` on a fully successful run. Slugs not present in `failed` are implicitly successful. |

### Three load-bearing data decisions

1. **Per-search scraping**, not scrape-everything. Notifier iterates active `saved_searches`, builds a Spitogatos URL per search. Scales linearly with users; refactor to scrape-once-match-many is contained to the notifier when needed.
2. **Cold-start UX = digest, not spam.** On `/new`, all currently-matching listings are inserted into `alerts_sent` immediately (no Telegram messages). The bot's confirmation includes "Found N matches — latest 3 below". Future runs only ping on truly new listings.
3. **Listing identity = Spitogatos's `external_id`.** Stable numeric ID embedded in their URLs. Survives relisting.

## 6. Telegram bot UX

### Commands

| Command | Behaviour |
|---|---|
| `/start` | Welcome message + how-to. Auto on first message. |
| `/new` | 4-step wizard: location → min price → max price → bedrooms. Inline keyboard buttons on each prompt. Implemented via `python-telegram-bot` `ConversationHandler`. |
| `/list` | List user's saved searches with IDs, status, and inline ⏸ Pause / 🗑 Delete buttons per row. |
| `/pause <id>`, `/resume <id>` | Toggle `saved_searches.is_active`. |
| `/delete <id>` | Confirm + delete. |
| `/help` | Command reference. |

### Two non-trivial UX decisions

1. **Wizard, not one-liner.** `/new` is conversational. Friendly for non-technical users; showcases `ConversationHandler` state-machine pattern. ~5-minute per-state timeout drops back to entry with a "no worries" message.
2. **Location is closed-set.** A static `locations.yml` in the repo maps ~50 Greek cities + Athens neighbourhoods to Spitogatos URL slugs. Bot uses `rapidfuzz` for matching; on miss, offers 3 closest as inline buttons. Avoids free-text fuzzy-match rabbit hole.

### Cold-start digest

Confirmation message after `/new`:
> Saved ✓
> *Athens Centre · €700–1200 · 2 BR*
>
> Found **14 current matches** — latest 3 below. New ones will arrive here as they appear.

**Source of "14 current matches": the `listings` table, filtered by the new saved search's criteria** — *not* a fresh inline scrape. This keeps the bot response under a second; the trade-off is that the digest reflects the last hourly scrape, which can be up to 60 minutes stale. Acceptable: the next scheduled scrape will catch any genuinely-new listings via the normal alert path. Avoids a synchronous 5–30s scrape inside a Telegram message handler.

All 14 are inserted into `alerts_sent` so the user is not flooded by the next hourly scrape.

## 7. Web app

### Stack

Next.js (App Router) + Tailwind, deployed to Vercel hobby. **Zero Next.js API routes used** — all data flows from FastAPI. Keeps the frontend/backend boundary honest.

### Pages

| Path | Type | Purpose |
|---|---|---|
| `/` | Static | Landing: hero, "Open in Telegram" CTA, live counters. |
| `/listings` | Client-rendered | Browse current listings, filters URL-synced (`?loc=...&min=...&max=...&br=...`). |
| `/listings/<location-slug>` | Static (build-time) | ~50 SEO routes generated from `locations.yml`. Revalidated every 60min. |
| `/about` | Static | How it works, link to GitHub. |
| `/healthz` | API endpoint | Public JSON: `{last_scrape, status, active_listings}`. |

### Reliability indicator

Footer pill sourced from `/healthz`:
- 🟢 *"Data fresh — updated 8 min ago"*
- 🟡 *"Last scrape was 2h ago — investigating"* (last `scrape_runs` >90min old)
- 🔴 *"Scraper currently down — showing cached listings"* (last run `status='failed'`)

The web app **never crashes** on scraper failure — serves last-known-good listings with the banner.

### Not in scope (MVP)

- Listing detail pages (link out to spitogatos.gr — no value-add hosting their photos)
- Web-side accounts, favouriting, history
- i18n (English-only; Greek translation a tidy v2 PR)
- Admin dashboard (use Postgres + Sentry)

## 8. Error handling and observability

### Failure modes

| Failure | Detection | Response |
|---|---|---|
| Spitogatos 5xx / network error | HTTP / exception | `tenacity`: 3 retries, exponential backoff. If all fail, mark this *one* search as failed in the run; continue others. |
| Spitogatos 403/429 (bot detection) | HTTP status | No retry. After **5 consecutive runs** majority-failed → circuit-broken: skip runs, status pill 🔴, Sentry alert. Manual intervention. |
| 200 response, parser finds 0 listings | Post-parse assertion | Almost certainly a layout change. Run `failed`, `error='zero_listings_on_200'`, Sentry alert. **Catches the #1 maintenance risk.** |
| DataImpulse proxy failure | Exception during fetch | Treated as 5xx — retry. |
| Telegram `sendMessage` fails | API response | 3 retries with backoff. On 403 *"bot blocked"* → set `users.deactivated_at`. |
| User abandons `/new` wizard | `ConversationHandler` 5-min timeout | Drops back to entry with "no worries, run /new again". |
| Web app can't reach backend | Client fetch error | Shell renders: "We're having trouble loading listings — the bot still works! [Open Telegram]". Never 500. |
| Empty filter result | API returns `[]` | Friendly empty state with prompt to set up a saved search. |
| Backend cold start | Fly auto-wake (~1s) | Next.js shows skeleton during fetch. |

### Two non-trivial error-handling decisions

1. **`alerts_sent` written AFTER Telegram succeeds.** Simpler than two-phase commit. Cost: rare duplicate ping if process crashes between Telegram 200 and DB insert. Tolerable; strictly better than silent message loss.
2. **Sentry is the only observability layer.** Free hobby tier (5k events/mo). One DSN across FastAPI / Next.js / bot. `structlog` with correlation IDs per scrape run for local debugging. No Prometheus / Datadog — overkill for the load.

### Secrets

All via Fly secrets / Vercel env vars. `config.py` retired entirely. `.env.example` checked in with empty values. Scraper config (URLs, headers, selector class names) stays in code, not env — breaking changes show up in PRs.

## 9. Testing strategy

| Layer | Tool | Coverage target |
|---|---|---|
| Parser | `pytest` against saved HTML fixtures in `tests/fixtures/spitogatos/` | 100% |
| Notifier diff logic | `pytest` (TDD) | 100% |
| DB layer / migrations | `pytest` + `testcontainers-postgres` | High — real Postgres, not SQLite |
| API endpoints | `httpx.AsyncClient` against FastAPI app | High |
| Bot handlers | `python-telegram-bot` test utilities | Wizard state transitions covered |
| Outbound HTTP | `respx` (mocks `httpx`) | All external calls mocked in CI |
| Frontend E2E | `playwright` against Vercel preview | One scripted journey: load /, browse, filter, see results |

### CI

GitHub Actions on PR: `ruff check` → `mypy` → `pytest` (with testcontainers Postgres) → frontend `pnpm lint/typecheck/build` → Playwright on preview deploy. ~3 min total.

`ruff` replaces the existing `black + flake8` setup — single tool, faster, modern.

### Daily live canary

`daily-canary.yml` (separate from CI): hits a known-busy Spitogatos URL through DataImpulse at 06:00 UTC, asserts ≥10 listings parse. Failure auto-opens a GitHub issue. The "Spitogatos changed HTML" alarm.

### Deliberately NOT in scope

- React component unit tests (presentational shells)
- Load / perf tests (no load)
- Coverage gates, mutation testing, fuzz testing

## 10. Out of scope (whole project, MVP)

- Multi-source aggregation (xe.gr, plot.gr) — clean v2 extension
- For-sale listings — alert value prop weak
- Advanced filters: m², furnished, parking, pets, floor — v2
- Sub-1-hour scrape cadence
- User accounts beyond Telegram
- Web app filter/alert configuration
- Per-listing detail pages
- i18n (English MVP, Greek PR-able)
- Price-drop tracking, days-on-market history

## 11. Open risks and mitigations

| Risk | Mitigation |
|---|---|
| Spitogatos changes HTML and breaks parser | Saved fixtures + daily live canary auto-opens GitHub issue within 24h |
| Spitogatos escalates bot detection | Circuit breaker + Sentry alert; worst case requires Playwright + more bandwidth (could end the project) |
| Free-tier policy changes (Fly, Neon, Vercel) | Re-platform on each — historically every 2 yrs. Acceptable maintenance cost |
| GitHub Actions cron drift | Acceptable — 1-hour cadence target tolerates minutes of jitter |
| GitHub Actions auto-disables on 60-day inactivity | Dependabot keeps the repo active monthly |
| Telegram bot abuse / spam | Out of scope for MVP — add rate limit per `telegram_chat_id` in v2 if needed |

## 12. What changes from today's code

The current state is a single `main.py` with hardcoded Marousi URL, gitignored `config.py` for proxy credentials, no tests, no UI. The implementation plan will:

1. Move `main.py` content into `backend/home_scanner/scraper/` as a proper module.
2. Retire `config.py` in favour of env vars.
3. Add the rest: `db`, `bot`, `api`, `notifier`, frontend, CI, deploy config.
4. Replace `black + flake8` with `ruff` in `pyproject.toml`.

This is greenfield in everything but the parser core — most of `main.py` is preserved as the seed of `scraper/`.

---

## Addendum (2026-05-11) — Source pivoted from spitogatos.gr to xe.gr

After Plan 2 deployed, the first live scrape returned `"zero_listings_on_200"` against spitogatos.gr. Root cause: Spitogatos uses F5 BIG-IP / Reese84 TLS+HTTP fingerprinting and serves a hydrated-by-JS Vue shell to non-browser clients. The DataImpulse residential proxy passed the IP-reputation check but the request fingerprint at the protocol level was rejected.

### Options evaluated

| | Cost | Effort | Verdict |
|---|---|---|---|
| Playwright (headless Chromium) | needs 512 MB Fly VM (~$2/mo more), Chromium adds 200 MB to image, 5–15 s per scrape | high | overbuilt for the data we need |
| Third-party scraping API (Apify/ScrapingBee/Bright Data Web Unlocker) | ~$5–50/mo at our volume | low code | "outsourced engineering" — wrong portfolio signal |
| `curl_cffi` (TLS-impersonating client) | $0 | ~30 min | fragile when defenders update fingerprints; viable fallback |
| **Pivot to xe.gr** | $0; drops DataImpulse | ~1–2 hr | clean SSR HTML, no WAF, explicit bedroom data per card |

### Decision

Pivoted to xe.gr. Trade-offs accepted:

- xe.gr has no public read API either — both providers require scraping. xe.gr's developer API is write-only for agencies posting listings.
- Location identifiers change from URL slugs (spitogatos) to Google Place IDs (xe.gr). `SavedSearch.location_slug` column kept its name; semantics now "the identifier we use for this location with the upstream source." `locations.yml` documents this.
- DataImpulse proxy becomes optional infrastructure (Settings fields kept, made non-required) for if we ever re-add spitogatos as a second source.

### What changed

- `scraper/parser.py` rewritten against real xe.gr HTML (fixture: `tests/fixtures/xe/thessaloniki-page1.html`). The `common-ad`/`property-ad-*` class taxonomy replaced spitogatos's `tile__*`. Bedroom count is now parsed directly from `<i class="xe-bedroom"></i><span>×N</span>` rather than inferred from title strings.
- `scraper/search_url.py` rewritten to build xe.gr URLs (`?item_type=re_residence&transaction_name=rent&geo_place_ids[]=<place_id>`). Price/bedroom filtering moved from URL params to DB-side post-scrape — xe.gr's filter param contract is undocumented and we don't want to depend on it.
- `scraper/client.py` renamed `SpitogatosClient` → `ListingClient`. Referer header switched to xe.gr.
- `locations.yml` rewritten with Google Place IDs for 14 major Greek areas. Process documented in README for adding more.
- `Settings`: DataImpulse env vars demoted from required to optional. `proxy_url` returns `None` when not configured.

### Risk update (replaces §11 row 1)

| Risk | Mitigation |
|---|---|
| ~~Spitogatos changes HTML and breaks parser~~ → **xe.gr changes HTML and breaks parser** | Same daily live canary catches it within 24h; canary URL updated to xe.gr's Thessaloniki rental search. |

The §8 zero-listings-on-200 canary detector worked exactly as designed — it caught the spitogatos block on the first live scrape, and the same detector would catch a future xe.gr markup change.
