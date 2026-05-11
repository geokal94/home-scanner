"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { LOCATIONS } from "@/lib/locations";

export function FilterBar() {
  const router = useRouter();
  const params = useSearchParams();

  const [location, setLocation] = useState(params.get("location") ?? "");
  const [priceMin, setPriceMin] = useState(params.get("price_min") ?? "");
  const [priceMax, setPriceMax] = useState(params.get("price_max") ?? "");
  const [bedroomsMin, setBedroomsMin] = useState(params.get("bedrooms_min") ?? "");

  function apply() {
    const next = new URLSearchParams();
    if (location) next.set("location", location);
    if (priceMin) next.set("price_min", priceMin);
    if (priceMax) next.set("price_max", priceMax);
    if (bedroomsMin) next.set("bedrooms_min", bedroomsMin);
    next.set("offset", "0");
    router.push(`/listings?${next.toString()}`);
  }

  return (
    <div className="grid grid-cols-2 gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4 md:grid-cols-5">
      <label className="text-sm">
        <span className="mb-1 block text-xs font-medium uppercase text-gray-500">
          Location
        </span>
        <select
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="w-full rounded border-gray-300 bg-white px-2 py-1.5 text-sm"
        >
          <option value="">All Greece</option>
          {LOCATIONS.map((loc) => (
            <option key={loc.url_slug} value={loc.name}>
              {loc.name}
            </option>
          ))}
        </select>
      </label>

      <label className="text-sm">
        <span className="mb-1 block text-xs font-medium uppercase text-gray-500">
          Min € / month
        </span>
        <input
          inputMode="numeric"
          value={priceMin}
          onChange={(e) => setPriceMin(e.target.value)}
          placeholder="—"
          className="w-full rounded border-gray-300 bg-white px-2 py-1.5 text-sm"
        />
      </label>

      <label className="text-sm">
        <span className="mb-1 block text-xs font-medium uppercase text-gray-500">
          Max € / month
        </span>
        <input
          inputMode="numeric"
          value={priceMax}
          onChange={(e) => setPriceMax(e.target.value)}
          placeholder="—"
          className="w-full rounded border-gray-300 bg-white px-2 py-1.5 text-sm"
        />
      </label>

      <label className="text-sm">
        <span className="mb-1 block text-xs font-medium uppercase text-gray-500">
          Min bedrooms
        </span>
        <select
          value={bedroomsMin}
          onChange={(e) => setBedroomsMin(e.target.value)}
          className="w-full rounded border-gray-300 bg-white px-2 py-1.5 text-sm"
        >
          <option value="">Any</option>
          <option value="0">Studio (0)</option>
          <option value="1">1+</option>
          <option value="2">2+</option>
          <option value="3">3+</option>
        </select>
      </label>

      <button
        type="button"
        onClick={apply}
        className="self-end rounded bg-gray-900 px-4 py-1.5 text-sm font-medium text-white hover:bg-gray-700"
      >
        Apply
      </button>
    </div>
  );
}
