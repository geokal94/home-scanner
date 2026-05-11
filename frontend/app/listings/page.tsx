import { fetchListings, type ListingsQuery } from "@/lib/api";
import { FilterBar } from "../_components/filter-bar";
import { ListingCard } from "../_components/listing-card";
import { Pagination } from "../_components/pagination";
import { EmptyState } from "../_components/empty-state";

export const dynamic = "force-dynamic"; // URL params change per request

const LIMIT = 24;

function parseQuery(searchParams: Record<string, string | undefined>): ListingsQuery {
  const q: ListingsQuery = { limit: LIMIT };
  if (searchParams.location) q.location = searchParams.location;
  if (searchParams.price_min) q.priceMin = Number(searchParams.price_min);
  if (searchParams.price_max) q.priceMax = Number(searchParams.price_max);
  if (searchParams.bedrooms_min) q.bedroomsMin = Number(searchParams.bedrooms_min);
  if (searchParams.bedrooms_max) q.bedroomsMax = Number(searchParams.bedrooms_max);
  if (searchParams.offset) q.offset = Number(searchParams.offset);
  return q;
}

export default async function ListingsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const params = await searchParams;
  const query = parseQuery(params);

  let data;
  try {
    data = await fetchListings(query);
  } catch {
    return (
      <div className="mx-auto max-w-6xl px-6 py-8">
        <FilterBar />
        <p className="mt-6 rounded-md bg-red-50 p-4 text-sm text-red-700">
          Couldn&apos;t load listings. The bot still works —{" "}
          <a
            href="https://t.me/home_scanner_gr_bot"
            className="font-medium underline"
          >
            open it in Telegram
          </a>
          .
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <FilterBar />

      <div className="mt-6 flex items-center justify-between text-sm text-gray-600">
        <span>
          Showing{" "}
          <strong>
            {data.offset + 1}–{Math.min(data.offset + data.limit, data.total)}
          </strong>{" "}
          of <strong>{data.total}</strong> listings
        </span>
      </div>

      <div className="mt-3">
        {data.listings.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
            {data.listings.map((listing) => (
              <ListingCard key={listing.id} listing={listing} />
            ))}
          </div>
        )}
      </div>

      <Pagination total={data.total} limit={data.limit} offset={data.offset} />
    </div>
  );
}
