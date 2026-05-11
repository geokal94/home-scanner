export function EmptyState() {
  return (
    <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
      <p className="text-gray-700">No listings match these filters.</p>
      <p className="mt-1 text-sm text-gray-500">
        Try broadening, or set up a saved search in the{" "}
        <a
          href="https://t.me/home_scanner_gr_bot"
          target="_blank"
          rel="noreferrer"
          className="text-sky-600 hover:underline"
        >
          Telegram bot
        </a>{" "}
        to get pinged when one appears.
      </p>
    </div>
  );
}
