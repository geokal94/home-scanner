// Typed fetch wrapper for the home-scanner FastAPI backend.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://home-scanner.fly.dev";

export type Listing = {
  id: number;
  external_id: string;
  url: string;
  title: string | null;
  price_eur: number;
  bedrooms: number | null;
  area_m2: number | null;
  location_text: string | null;
  first_seen_at: string;
  last_seen_at: string;
};

export type ListingsResponse = {
  total: number;
  limit: number;
  offset: number;
  listings: Listing[];
};

export type HealthResponse = {
  status: "ok" | "degraded" | "down";
  last_scrape: {
    started_at: string;
    status: "ok" | "failed" | "running";
    minutes_ago: number;
  } | null;
  active_listings: number;
};

export type ListingsQuery = {
  location?: string;
  priceMin?: number;
  priceMax?: number;
  bedroomsMin?: number;
  bedroomsMax?: number;
  limit?: number;
  offset?: number;
};

function buildQueryString(q: ListingsQuery): string {
  const params = new URLSearchParams();
  if (q.location) params.set("location", q.location);
  if (q.priceMin !== undefined) params.set("price_min", String(q.priceMin));
  if (q.priceMax !== undefined) params.set("price_max", String(q.priceMax));
  if (q.bedroomsMin !== undefined) params.set("bedrooms_min", String(q.bedroomsMin));
  if (q.bedroomsMax !== undefined) params.set("bedrooms_max", String(q.bedroomsMax));
  if (q.limit !== undefined) params.set("limit", String(q.limit));
  if (q.offset !== undefined) params.set("offset", String(q.offset));
  return params.toString();
}

export async function fetchListings(
  q: ListingsQuery,
  signal?: AbortSignal,
): Promise<ListingsResponse> {
  const qs = buildQueryString(q);
  const url = `${API_URL}/listings${qs ? `?${qs}` : ""}`;
  const res = await fetch(url, { signal, next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`fetchListings: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/healthz`, {
    signal,
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`fetchHealth: ${res.status} ${res.statusText}`);
  return res.json();
}
