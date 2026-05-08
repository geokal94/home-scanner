"""Greek-area location registry, sourced from `locations.yml`.

Provides Spitogatos URL-slug lookup with fuzzy matching for the bot's /new wizard.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from rapidfuzz import fuzz, process

_YAML_PATH = Path(__file__).parent / "locations.yml"
_FUZZ_CUTOFF = 70  # 0-100; below this we report no match


@dataclass(frozen=True, slots=True)
class Location:
    name: str
    slug: str
    aliases: tuple[str, ...]

    @property
    def search_terms(self) -> tuple[str, ...]:
        return (self.name.lower(), *self.aliases)


@lru_cache(maxsize=1)
def load_locations() -> list[Location]:
    raw = yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))
    return [
        Location(
            name=entry["name"],
            slug=entry["slug"],
            aliases=tuple(a.lower() for a in entry.get("aliases", [])),
        )
        for entry in raw
    ]


def find_locations(query: str, limit: int = 5) -> list[Location]:
    """Return up to `limit` Locations whose name or aliases best match `query`.

    Returns empty list if `query` is empty or no match passes the cutoff.
    """
    query = query.strip().lower()
    if not query:
        return []

    locations = load_locations()
    # Build a flat list of (search_term → location) pairs for fuzzy matching
    term_to_loc: dict[str, Location] = {}
    for loc in locations:
        for term in loc.search_terms:
            term_to_loc[term] = loc

    matches = process.extract(
        query,
        term_to_loc.keys(),
        scorer=fuzz.WRatio,
        limit=limit * 3,  # over-fetch to dedupe
        score_cutoff=_FUZZ_CUTOFF,
    )

    seen_slugs: set[str] = set()
    out: list[Location] = []
    for term, _score, _idx in matches:
        loc = term_to_loc[term]
        if loc.slug not in seen_slugs:
            seen_slugs.add(loc.slug)
            out.append(loc)
            if len(out) == limit:
                break
    return out
