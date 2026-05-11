import { notFound } from "next/navigation";
import { fetchListings } from "@/lib/api";
import { LOCATIONS, locationByUrlSlug } from "@/lib/locations";
import { ListingCard } from "../../_components/listing-card";
import { Pagination } from "../../_components/pagination";
import { EmptyState } from "../../_components/empty-state";
import { FilterBar } from "../../_components/filter-bar";

export const revalidate = 3600; // Re-render at most once per hour

const LIMIT = 24;

export function generateStaticParams() {
  return LOCATIONS.map((loc) => ({ slug: loc.url_slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const loc = locationByUrlSlug(slug);
  if (!loc) return {};
  return {
    title: `Rentals in ${loc.name} — home-scanner`,
    description: `Find rental apartments in ${loc.name}, Greece, via xe.gr aggregation.`,
  };
}

export default async function LocationPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const { slug } = await params;
  const loc = locationByUrlSlug(slug);
  if (!loc) notFound();

  const sp = await searchParams;
  const offset = sp.offset ? Number(sp.offset) : 0;

  let data;
  try {
    data = await fetchListings({
      location: loc.name,
      limit: LIMIT,
      offset,
    });
  } catch {
    return (
      <div className="mx-auto max-w-6xl px-6 py-8">
        <p className="text-red-700">Couldn&apos;t load listings for {loc.name}.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="mb-2 text-2xl font-bold">Rentals in {loc.name}</h1>
      <p className="mb-6 text-sm text-gray-600">
        {data.total} active {data.total === 1 ? "listing" : "listings"} from xe.gr.
      </p>

      <FilterBar />

      <div className="mt-6">
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
