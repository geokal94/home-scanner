import Link from "next/link";
import { LOCATIONS } from "@/lib/locations";
import { fetchHealth } from "@/lib/api";

export const revalidate = 60;

export default async function HomePage() {
  let activeListings: number | null = null;
  let minutesAgo: number | null = null;
  try {
    const health = await fetchHealth();
    activeListings = health.active_listings;
    minutesAgo = health.last_scrape?.minutes_ago ?? null;
  } catch {
    // graceful — fall through with nulls
  }

  return (
    <>
      {/* Hero with subtle gradient backdrop */}
      <section className="relative overflow-hidden bg-gradient-to-br from-sky-50 via-white to-indigo-50">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-sky-200 opacity-30 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-32 left-1/3 h-96 w-96 rounded-full bg-indigo-200 opacity-20 blur-3xl"
        />

        <div className="relative mx-auto max-w-4xl px-6 py-20 md:py-28">
          <span className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-white/60 px-3 py-1 text-xs font-medium text-sky-700 shadow-sm backdrop-blur-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Live · scrapes xe.gr every hour
          </span>

          <h1 className="mt-6 text-5xl font-bold tracking-tight text-gray-900 md:text-6xl">
            Watch Greek rentals.{" "}
            <span className="bg-gradient-to-r from-sky-600 to-indigo-600 bg-clip-text text-transparent">
              Get pinged when one matches.
            </span>
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-gray-600 md:text-xl">
            home-scanner watches{" "}
            <a
              href="https://www.xe.gr/property"
              target="_blank"
              rel="noreferrer"
              className="font-medium text-sky-600 hover:underline"
            >
              xe.gr
            </a>{" "}
            for new apartment listings matching your filters and pings you on
            Telegram within the hour.
          </p>

          <div className="mt-10 flex flex-wrap items-center gap-3">
            <a
              href="https://t.me/home_scanner_gr_bot"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-sky-600 px-6 py-3 font-semibold text-white shadow-lg shadow-sky-600/20 transition hover:bg-sky-700 hover:shadow-xl"
            >
              Open Telegram bot
              <span aria-hidden>→</span>
            </a>
            <Link
              href="/listings"
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-6 py-3 font-semibold text-gray-700 transition hover:border-gray-400 hover:bg-gray-50"
            >
              Browse listings
            </Link>
          </div>

          {activeListings !== null && (
            <p className="mt-8 text-sm text-gray-500">
              Watching{" "}
              <strong className="text-gray-700">
                {activeListings.toLocaleString()}
              </strong>{" "}
              active listings
              {minutesAgo !== null && <> · last update {minutesAgo} min ago</>}
            </p>
          )}
        </div>
      </section>

      {/* Locations strip */}
      <section className="mx-auto max-w-4xl px-6 py-16">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
          Browse by location
        </h2>
        <div className="mt-4 flex flex-wrap gap-2 text-sm">
          {LOCATIONS.map((loc) => (
            <Link
              key={loc.url_slug}
              href={`/listings/${loc.url_slug}`}
              className="rounded-full border border-gray-200 bg-white px-4 py-1.5 font-medium text-gray-700 shadow-sm transition hover:-translate-y-0.5 hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700 hover:shadow"
            >
              {loc.name}
            </Link>
          ))}
        </div>
      </section>

      {/* How it works strip */}
      <section className="border-t border-gray-200 bg-gray-50">
        <div className="mx-auto grid max-w-4xl gap-8 px-6 py-16 md:grid-cols-3">
          <Step
            n={1}
            title="Set up your filters"
            body="Pick a location, price range, and bedroom count in the Telegram bot."
          />
          <Step
            n={2}
            title="We scrape every hour"
            body="A background job watches xe.gr for new postings matching your search."
          />
          <Step
            n={3}
            title="You get pinged first"
            body="New listings are forwarded to your Telegram within minutes of being posted."
          />
        </div>
      </section>
    </>
  );
}

function Step({ n, title, body }: { n: number; title: string; body: string }) {
  return (
    <div>
      <div className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-sky-600 text-sm font-bold text-white">
        {n}
      </div>
      <h3 className="mt-4 text-base font-semibold text-gray-900">{title}</h3>
      <p className="mt-1 text-sm text-gray-600">{body}</p>
    </div>
  );
}
