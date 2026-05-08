import httpx
import pytest
import respx
from home_scanner.scraper.client import SpitogatosClient, ScrapeError


@pytest.fixture
def client() -> SpitogatosClient:
    return SpitogatosClient(proxy_url="http://u:p@proxy.example.com:823")


@respx.mock
def test_fetch_returns_html_on_200(client: SpitogatosClient):
    respx.get("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi").mock(
        return_value=httpx.Response(200, text="<html>ok</html>"),
    )
    html = client.fetch("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi")
    assert html == "<html>ok</html>"


@respx.mock
def test_fetch_retries_on_503_then_succeeds(client: SpitogatosClient):
    route = respx.get("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi")
    route.side_effect = [
        httpx.Response(503),
        httpx.Response(503),
        httpx.Response(200, text="<html>ok</html>"),
    ]
    html = client.fetch("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi")
    assert html == "<html>ok</html>"
    assert route.call_count == 3


@respx.mock
def test_fetch_raises_after_max_retries(client: SpitogatosClient):
    respx.get("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi").mock(
        return_value=httpx.Response(503),
    )
    with pytest.raises(ScrapeError):
        client.fetch("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi")


@respx.mock
def test_fetch_does_not_retry_on_403(client: SpitogatosClient):
    route = respx.get("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi").mock(
        return_value=httpx.Response(403),
    )
    with pytest.raises(ScrapeError, match="403"):
        client.fetch("https://www.spitogatos.gr/enoikiaseis-katoikies/marousi")
    assert route.call_count == 1
