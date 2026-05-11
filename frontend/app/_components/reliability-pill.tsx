// Polls /healthz and renders a green/yellow/red status pill.

import { fetchHealth } from "@/lib/api";

const PILL_STYLES = {
  ok: "bg-green-100 text-green-700",
  degraded: "bg-yellow-100 text-yellow-700",
  down: "bg-red-100 text-red-700",
} as const;

const DOT_STYLES = {
  ok: "bg-green-500",
  degraded: "bg-yellow-500",
  down: "bg-red-500",
} as const;

export async function ReliabilityPill() {
  let status: "ok" | "degraded" | "down";
  let message: string;
  try {
    const health = await fetchHealth();
    status = health.status;
    if (status === "ok" && health.last_scrape) {
      message = `Data fresh — updated ${health.last_scrape.minutes_ago} min ago`;
    } else if (status === "degraded" && health.last_scrape) {
      message = `Last scrape was ${health.last_scrape.minutes_ago} min ago — investigating`;
    } else {
      message = "Scraper currently down — showing cached listings";
    }
  } catch {
    status = "down";
    message = "Backend unreachable";
  }

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${PILL_STYLES[status]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${DOT_STYLES[status]}`} />
      {message}
    </span>
  );
}
