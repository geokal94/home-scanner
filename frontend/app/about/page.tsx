export const metadata = {
  title: "About — home-scanner",
};

export default function AboutPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16 prose prose-gray">
      <h1>How it works</h1>
      <p>
        home-scanner is a small open-source service that watches{" "}
        <a href="https://www.xe.gr/property">xe.gr</a> for new Greek apartment
        rentals and alerts you on Telegram when one matches your filters.
      </p>

      <h2>The pipeline</h2>
      <ol>
        <li>
          You configure a saved search in the{" "}
          <a href="https://t.me/home_scanner_gr_bot">Telegram bot</a> — location,
          price range, bedroom count.
        </li>
        <li>
          Every hour, a GitHub Actions cron triggers our scraper. It fetches the
          relevant xe.gr search pages, parses each listing card, and stores any
          new ones in Postgres.
        </li>
        <li>
          For each saved search, we diff the newly-seen listings against the ones
          we&apos;ve already alerted you about, and send a Telegram message for
          each genuinely new match.
        </li>
      </ol>

      <h2>What we don&apos;t do</h2>
      <ul>
        <li>We don&apos;t host listing photos — clicks go straight to xe.gr.</li>
        <li>We don&apos;t store your personal data beyond your Telegram chat ID.</li>
        <li>We don&apos;t republish xe.gr&apos;s content — we link to the source.</li>
      </ul>

      <h2>Open source</h2>
      <p>
        Source on GitHub:{" "}
        <a href="https://github.com/geokal94/home-scanner">geokal94/home-scanner</a>
        . MIT license. The design spec, implementation plans, and architecture
        notes are all in the repo.
      </p>
    </main>
  );
}
