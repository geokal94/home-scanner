from home_scanner.locations import Location, find_locations, load_locations


def test_load_locations_returns_list_of_location():
    locs = load_locations()
    assert len(locs) > 10
    assert all(isinstance(loc, Location) for loc in locs)
    assert all(loc.slug and loc.name for loc in locs)


def test_find_locations_exact_match_returns_top():
    matches = find_locations("Marousi")
    assert matches[0].slug == "marousi"


def test_find_locations_alias_match():
    matches = find_locations("Παγκράτι")
    assert matches[0].slug == "pagrati"


def test_find_locations_typo_returns_close_matches():
    matches = find_locations("athin centre")
    slugs = [m.slug for m in matches[:3]]
    assert "athina-kentro" in slugs


def test_find_locations_empty_query_returns_empty():
    assert find_locations("") == []


def test_find_locations_no_match_returns_empty():
    matches = find_locations("xyzzy nowhere")
    assert matches == []
