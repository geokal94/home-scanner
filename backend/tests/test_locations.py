from home_scanner.locations import Location, find_locations, load_locations

# Stable Google Place ID for Thessaloniki in our locations.yml.
PLACE_ID_THESSALONIKI = "ChIJ7eAoFPQ4qBQRqXTVuBXnugk"
PLACE_ID_PIRAEUS = "ChIJRzGst-u7oRQR9_0w_5XaINg"


def test_load_locations_returns_list_of_location():
    locs = load_locations()
    assert len(locs) > 10
    assert all(isinstance(loc, Location) for loc in locs)
    assert all(loc.slug and loc.name for loc in locs)
    # `slug` now stores Google Place IDs, which all start with "ChIJ"
    assert all(loc.slug.startswith("ChIJ") for loc in locs)


def test_find_locations_exact_match_returns_top():
    matches = find_locations("Thessaloniki")
    assert matches[0].slug == PLACE_ID_THESSALONIKI


def test_find_locations_alias_match():
    matches = find_locations("πειραιάς")
    assert matches[0].slug == PLACE_ID_PIRAEUS


def test_find_locations_typo_returns_close_matches():
    matches = find_locations("piraus")  # missing 'e'
    slugs = [m.slug for m in matches[:3]]
    assert PLACE_ID_PIRAEUS in slugs


def test_find_locations_empty_query_returns_empty():
    assert find_locations("") == []


def test_find_locations_no_match_returns_empty():
    matches = find_locations("xyzzy nowhere")
    assert matches == []
