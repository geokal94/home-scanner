import type { Listing } from "@/lib/api";

function isNew(listing: Listing): boolean {
  const ageMs = Date.now() - new Date(listing.first_seen_at).getTime();
  return ageMs < 24 * 60 * 60 * 1000;
}

export function ListingCard({ listing }: { listing: Listing }) {
  const newBadge = isNew(listing);
  const locationLabel = listing.location_text?.split(" | ")[0] ?? null;

  return (
    <a
      href={listing.url}
      target="_blank"
      rel="noreferrer"
      className="group relative block overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-lg"
    >
      <div className="relative aspect-[4/3] overflow-hidden bg-gradient-to-br from-sky-50 to-indigo-100">
        {listing.image_url ? (
          // Using <img>, not next/image — xe.gr CDN serves cropped 640x480
          // thumbnails already; next/image's optimizer would re-fetch and
          // re-encode them through Vercel (paid bandwidth for no gain).
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={listing.image_url}
            alt={listing.title ?? "Listing thumbnail"}
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center px-4 text-center text-xs font-medium text-sky-700/60">
            {listing.title ?? "No image"}
          </div>
        )}

        {newBadge && (
          <span className="absolute left-3 top-3 rounded-full bg-emerald-500/95 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white shadow-sm backdrop-blur-sm">
            New
          </span>
        )}
        <div className="absolute right-3 top-3 rounded-full bg-white/95 px-3 py-1 text-sm font-bold text-gray-900 shadow-sm backdrop-blur-sm">
          €{listing.price_eur.toLocaleString()}
        </div>
      </div>

      <div className="space-y-2 p-4">
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-gray-600">
          {listing.bedrooms !== null && (
            <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5">
              🛏 {listing.bedrooms === 0 ? "Studio" : `${listing.bedrooms} BR`}
            </span>
          )}
          {listing.area_m2 !== null && (
            <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5">
              📐 {listing.area_m2} m²
            </span>
          )}
        </div>
        {locationLabel && (
          <div className="truncate text-sm font-medium text-gray-700">
            {locationLabel}
          </div>
        )}
        <div className="pt-1 text-xs font-medium text-sky-600 transition-colors group-hover:text-sky-700">
          View on xe.gr →
        </div>
      </div>
    </a>
  );
}
