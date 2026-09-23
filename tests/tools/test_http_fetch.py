import httpx
import pytest

from evidence_graph.state import CountryCode
from evidence_graph.tools import ToolPolicyError, ToolUnavailableError
from evidence_graph.tools.http_fetch import HttpFetcher, html_to_text
from evidence_graph.use_cases.ev_incentives import allowlists

PAGE = """<html><head><title>Electric Car Grant<!-- --> - GOV.UK</title>
<script>var tracking = 1;</script></head>
<body><nav>Home | Menu</nav>
<main><h1>Electric Car Grant</h1><p>The maximum discount is &pound;3,750.</p></main>
<footer>Cookies</footer></body></html>"""


def fetcher(handler, **kwargs) -> HttpFetcher:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpFetcher(allowlists(), client=client, **kwargs)


def html(body: str = PAGE, status: int = 200) -> httpx.Response:
    return httpx.Response(status, text=body, headers={"content-type": "text/html; charset=utf-8"})


def test_html_to_text_keeps_main_content_and_drops_scripts_and_navigation():
    title, text = html_to_text(PAGE)

    assert title == "Electric Car Grant - GOV.UK"
    assert "£3,750" in text
    assert "tracking" not in text
    assert "Menu" not in text
    assert "Cookies" not in text


def test_fetch_returns_readable_page():
    page = fetcher(lambda request: html()).fetch("https://www.gov.uk/grant", CountryCode.UK)

    assert page.url == "https://www.gov.uk/grant"
    assert "£3,750" in page.text


def test_redirect_inside_the_allowlist_is_followed_and_final_url_kept():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        return html()

    page = fetcher(handler).fetch("https://www.gov.uk/old", CountryCode.UK)

    assert page.url == "https://www.gov.uk/new"


def test_redirect_off_the_allowlist_is_refused():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://blog.example.com/ev"})

    with pytest.raises(ToolPolicyError):
        fetcher(handler).fetch("https://www.gov.uk/old", CountryCode.UK)


def test_redirect_loops_are_bounded():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://www.gov.uk/loop"})

    with pytest.raises(ToolUnavailableError, match="redirects"):
        fetcher(handler, max_redirects=3).fetch("https://www.gov.uk/loop", CountryCode.UK)


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (html(status=403), "HTTP 403"),
        (httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"}), "type"),
        (html(body="x" * 20_000), "larger than"),
    ],
)
def test_unusable_responses_raise_tool_unavailable(response, message):
    with pytest.raises(ToolUnavailableError, match=message):
        fetcher(lambda request: response, max_bytes=10_000).fetch(
            "https://www.gov.uk/page", CountryCode.UK
        )


def test_network_errors_become_tool_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow", request=request)

    with pytest.raises(ToolUnavailableError, match="ConnectTimeout"):
        fetcher(handler).fetch("https://www.gov.uk/page", CountryCode.UK)


def test_page_text_is_capped():
    body = "<main>" + "evidence " * 1000 + "</main>"
    page = fetcher(lambda request: html(body), max_chars=1_000).fetch(
        "https://www.gov.uk/long", CountryCode.UK
    )

    assert len(page.text) == 1_000
