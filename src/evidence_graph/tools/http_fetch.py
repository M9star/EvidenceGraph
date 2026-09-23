import re
from collections.abc import Mapping
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

from evidence_graph.state.models import CountryCode
from evidence_graph.tools.base import FetchedPage, ToolPolicyError, ToolUnavailableError
from evidence_graph.tools.policy import is_allowed

ALLOWED_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
USER_AGENT = "EvidenceGraph/0.1 (research bot; official sources only)"

_SKIP_TAGS = frozenset(
    {"script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form",
     "template", "iframe", "button", "select"}
)  # fmt: skip
_BLOCK_TAGS = frozenset(
    {"p", "div", "section", "article", "main", "br", "li", "ul", "ol", "tr", "table",
     "h1", "h2", "h3", "h4", "h5", "h6", "dt", "dd", "blockquote"}
)  # fmt: skip
_MIN_MAIN_CHARS = 200


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._main_depth = 0
        self._all: list[str] = []
        self._main: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "main":
            self._main_depth += 1
        if tag in _BLOCK_TAGS:
            self._emit("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == "main" and self._main_depth:
            self._main_depth -= 1
        if tag in _BLOCK_TAGS:
            self._emit("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif not self._skip_depth:
            self._emit(data)

    def _emit(self, text: str) -> None:
        self._all.append(text)
        if self._main_depth:
            self._main.append(text)

    def text(self) -> str:
        main = _clean("".join(self._main))
        return main if len(main) >= _MIN_MAIN_CHARS else _clean("".join(self._all))


def _clean(text: str) -> str:
    lines = (re.sub(r"[ \t\r\f\v\u00a0]+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def html_to_text(html: str) -> tuple[str, str]:
    """Return (title, readable text), preferring <main> and dropping navigation and scripts."""
    parser = _TextExtractor()
    parser.feed(html)
    parser.close()
    title = " ".join(re.sub(r"<!--.*?-->", "", parser.title).split())
    return title, parser.text()


class HttpFetcher:
    """Fetches official pages with timeouts, a size cap, and allowlist checks on every redirect."""

    def __init__(
        self,
        allowlists: Mapping[CountryCode, frozenset[str]],
        timeout_s: float = 20.0,
        max_bytes: int = 3_000_000,
        max_chars: int = 40_000,
        max_redirects: int = 5,
        client: httpx.Client | None = None,
    ) -> None:
        self._allowlists = allowlists
        self._max_bytes = max_bytes
        self._max_chars = max_chars
        self._max_redirects = max_redirects
        self._client = client or httpx.Client(timeout=timeout_s, headers={"User-Agent": USER_AGENT})

    def fetch(self, url: str, country: CountryCode) -> FetchedPage:
        domains = self._allowlists.get(country, frozenset())
        for _ in range(self._max_redirects + 1):
            if not is_allowed(url, domains):
                raise ToolPolicyError(f"{url} is outside the {country} allowlist")
            try:
                with self._client.stream("GET", url, follow_redirects=False) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers.get("location", ""))
                        continue
                    return self._read(url, response)
            except httpx.HTTPError as exc:
                raise ToolUnavailableError(f"fetch {url}: {type(exc).__name__}") from exc
        raise ToolUnavailableError(f"fetch {url}: more than {self._max_redirects} redirects")

    def _read(self, url: str, response: httpx.Response) -> FetchedPage:
        if response.status_code != 200:
            raise ToolUnavailableError(f"fetch {url}: HTTP {response.status_code}")
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ToolUnavailableError(f"fetch {url}: unsupported content type {content_type!r}")

        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > self._max_bytes:
                raise ToolUnavailableError(f"fetch {url}: larger than {self._max_bytes} bytes")
        raw = body.decode(response.encoding or "utf-8", errors="replace")

        if content_type == "text/plain":
            title, text = url, _clean(raw)
        else:
            title, text = html_to_text(raw)
        return FetchedPage(
            url=url,
            title=title or url,
            text=text[: self._max_chars],
            retrieved_at=datetime.now(UTC),
        )
