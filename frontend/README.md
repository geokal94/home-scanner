# home-scanner frontend

Next.js 16 (App Router) + Tailwind 4 + TypeScript. Public landing page,
browseable listings, per-area routes. Pure consumer of the FastAPI backend —
no Next.js API routes are used.

## Stack

- **Next.js 16** with the App Router; pages live under `app/`.
- **Tailwind v4** (zero-config; plugins loaded via `@plugin` directive in `globals.css`).
- **pnpm** as the package manager (lockfile committed; `onlyBuiltDependencies`
  declared in `pnpm-workspace.yaml`).
- **Playwright** for the one end-to-end smoke test (`tests/e2e/`).

## Local development

```bash
pnpm install
echo 'NEXT_PUBLIC_API_URL=https://home-scanner.fly.dev' > .env.local
pnpm dev
```

Open `http://localhost:3000`.

To run against a local backend instead, replace the URL with `http://localhost:8080`
(or wherever your `python -m home_scanner serve` is listening).

## Build

```bash
pnpm build
```

The `prebuild` script (`scripts/generate-locations.mjs`) reads
`../backend/home_scanner/locations.yml` and writes `lib/locations.json`, so
the frontend always ships the current location set without duplicating the
YAML.

## Routes

| Path | Rendering |
|---|---|
| `/` | static + ISR (60s) — landing page, fetches counters from `/healthz` |
| `/about` | static — how-it-works copy |
| `/listings` | dynamic — filter-bar + listing grid + pagination, reads URL query params |
| `/listings/[slug]` | dynamic + ISR (1h) — per-area page; `generateStaticParams` enumerates `locations.yml` for SEO |

## Tests

```bash
# In one terminal:
pnpm dev

# In another:
pnpm test:e2e
```

Or `pnpm exec playwright test --list` to verify the test config without running them.
GitHub Actions runs these against every successful Vercel deployment
(`.github/workflows/frontend-e2e.yml`).

## Environment variables

| Variable | Where set |
|---|---|
| `NEXT_PUBLIC_API_URL` | Vercel project settings (production) + `.env.local` (dev) |

That's the only one. Everything else (backend secrets) lives on Fly.
