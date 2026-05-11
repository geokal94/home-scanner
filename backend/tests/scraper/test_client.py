import httpx
import pytest
import respx

from home_scanner.scraper.client import ListingClient, ScrapeError


@pytest.fixture
def client() -> ListingClient:
    return ListingClient(proxy_url="http://u:p@proxy.example.com:823")


@respx.mock
def test_fetch_returns_html_on_200(client: ListingClient):
    respx.get("https://www.xe.gr/property/results?location=marousi").mock(
        return_value=httpx.Response(200, text="<html>ok</html>"),
    )
    html = client.fetch("https://www.xe.gr/property/results?location=marousi")
    assert html == "<html>ok</html>"


@respx.mock
def test_fetch_retries_on_503_then_succeeds(client: ListingClient):
    route = respx.get("https://www.xe.gr/property/results?location=marousi")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(503),
        httpx.Response(200, text="<html>ok</html>"),
    ]
    html = client.fetch("https://www.xe.gr/property/results?location=marousi")
    assert html == "<html>ok</html>"
    assert route.call_count == 3


@respx.mock
def test_fetch_raises_after_max_retries(client: ListingClient):
    respx.get("https://www.xe.gr/property/results?location=marousi").mock(
        return_value=httpx.Response(503),
    )
    with pytest.raises(ScrapeError):
        client.fetch("https://www.xe.gr/property/results?location=marousi")


@respx.mock
def test_fetch_does_not_retry_on_403(client: ListingClient):
    route = respx.get("https://www.xe.gr/property/results?location=marousi").mock(
        return_value=httpx.Response(403),
    )
    with pytest.raises(ScrapeError, match="403"):
        client.fetch("https://www.xe.gr/property/results?location=marousi")
    assert route.call_count == 1
