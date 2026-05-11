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
    <main className="mx-auto max-w-4xl px-6 py-16">
      <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
        Watch Greek rentals.{" "}
        <span className="text-sky-600">Get pinged when one matches.</span>
      </h1>
      <p className="mt-4 max-w-xl text-lg text-gray-600">
        home-scanner watches{" "}
        <a
          href="https://www.xe.gr/property"
          target="_blank"
          rel="noreferrer"
          className="text-sky-600 hover:underline"
        >
          xe.gr
        </a>{" "}
        for new apartment listings matching your filters and pings you on Telegram
        within the hour.
      </p>

      <div className="mt-8 flex gap-4">
        <a
          href="https://t.me/home_scanner_gr_bot"
          target="_blank"
          rel="noreferrer"
          className="rounded-md bg-sky-600 px-6 py-3 font-medium text-white hover:bg-sky-700"
        >
          Open Telegram bot
        </a>
        <Link
          href="/listings"
          className="rounded-md border border-gray-300 px-6 py-3 font-medium text-gray-700 hover:bg-gray-50"
        >
          Browse current listings →
        </Link>
      </div>

      {activeListings !== null && (
        <p className="mt-6 text-sm text-gray-500">
          Watching <strong>{activeListings.toLocaleString()}</strong> active
          listings
          {minutesAgo !== null && (
            <> · last update {minutesAgo} min ago</>
          )}
        </p>
      )}

      <section className="mt-16">
        <h2 className="text-lg font-semibold">Browse by location</h2>
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          {LOCATIONS.map((loc) => (
            <Link
              key={loc.url_slug}
              href={`/listings/${loc.url_slug}`}
              className="rounded-full border border-gray-200 px-3 py-1 text-gray-700 hover:border-gray-300 hover:bg-gray-50"
            >
              {loc.name}
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
