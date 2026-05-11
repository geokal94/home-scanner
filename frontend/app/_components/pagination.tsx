"use client";

import { useRouter, useSearchParams } from "next/navigation";

export function Pagination({
  total,
  limit,
  offset,
}: {
  total: number;
  limit: number;
  offset: number;
}) {
  const router = useRouter();
  const params = useSearchParams();

  function go(newOffset: number) {
    const next = new URLSearchParams(params);
    next.set("offset", String(newOffset));
    router.push(`/listings?${next.toString()}`);
  }

  const page = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  if (totalPages <= 1) return null;

  return (
    <nav className="flex items-center justify-center gap-2 py-6 text-sm">
      <button
        onClick={() => go(Math.max(0, offset - limit))}
        disabled={offset === 0}
        className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
      >
        ←
      </button>
      <span className="text-gray-600">
        Page {page} of {totalPages}
      </span>
      <button
        onClick={() => go(offset + limit)}
        disabled={page >= totalPages}
        className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
      >
        →
      </button>
    </nav>
  );
}
