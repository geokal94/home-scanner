import type { Listing } from "@/lib/api";

function isNew(listing: Listing): boolean {
  const ageMs = Date.now() - new Date(listing.first_seen_at).getTime();
  return ageMs < 24 * 60 * 60 * 1000;
}

export function ListingCard({ listing }: { listing: Listing }) {
  const newBadge = isNew(listing);
  return (
    <a
      href={listing.url}
      target="_blank"
      rel="noreferrer"
      className="group block overflow-hidden rounded-lg border border-gray-200 bg-white transition hover:border-gray-300 hover:shadow-sm"
    >
      <div className="flex h-32 items-center justify-center bg-gradient-to-br from-sky-50 to-indigo-50 text-xs text-sky-700">
        {listing.title ?? "Listing"}
      </div>
      <div className="space-y-1 p-3">
        <div className="flex items-baseline justify-between">
          <span className="text-lg font-bold">
            €{listing.price_eur.toLocaleString()}
          </span>
          {newBadge && (
            <span className="rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-green-700">
              New
            </span>
          )}
        </div>
        <div className="text-xs text-gray-600">
          {listing.bedrooms !== null && (
            <span className="mr-2">🛏 {listing.bedrooms} BR</span>
          )}
          {listing.area_m2 !== null && <span>📐 {listing.area_m2} m²</span>}
        </div>
        {listing.location_text && (
          <div className="truncate text-xs text-gray-500">{listing.location_text}</div>
        )}
        <div className="pt-1 text-xs text-sky-600 group-hover:underline">
          View on xe.gr →
        </div>
      </div>
    </a>
  );
}
