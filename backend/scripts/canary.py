"""Live Spitogatos parser canary.

Hits a known-busy rental search URL through DataImpulse and asserts the parser
returns at least N listings. Run from CI; non-zero exit if the assertion fails.

Per spec §9, this is the alarm that catches Spitogatos HTML changes within 24h
rather than weeks.
"""
from __future__ import annotations

import sys

from home_scanner.scraper import SearchFilter, SpitogatosClient, scrape_search
from home_scanner.settings import Settings

MIN_EXPECTED_LISTINGS = 10
CANARY_LOCATION = "athina-kentro"  # Always-busy reference search


def main() -> int:
    settings = Settings()
    client = SpitogatosClient(proxy_url=settings.proxy_url)
    f = SearchFilter(location_slug=CANARY_LOCATION)

    listings = scrape_search(f, client=client)
    print(f"canary: parsed {len(listings)} listings from {CANARY_LOCATION}")

    if len(listings) < MIN_EXPECTED_LISTINGS:
        print(
            f"canary: FAIL — expected at least {MIN_EXPECTED_LISTINGS}, got {len(listings)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
