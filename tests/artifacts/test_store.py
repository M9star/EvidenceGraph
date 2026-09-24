from datetime import UTC, datetime

from evidence_graph.artifacts import InMemoryArtifactStore
from evidence_graph.state import CountryCode
from evidence_graph.tools.artifacts import ArtifactToolkit
from evidence_graph.tools.base import FetchedPage, SearchHit

HUGE = "x" * 50_000
PAGE = FetchedPage(
    url="https://www.gov.uk/electric-car-grant",
    title="Grant",
    text=HUGE,
    retrieved_at=datetime(2026, 9, 24, tzinfo=UTC),
)


class HugeToolkit:
    def search(self, query, country):
        return [SearchHit(url=PAGE.url, title=PAGE.title)]

    def fetch(self, url, country):
        return PAGE

    def extract(self, page, country, feedback=None):
        return []


def test_store_is_content_addressed():
    store = InMemoryArtifactStore()
    first = store.put("hello")
    second = store.put("hello")

    assert first == second
    assert store.get(first) == "hello"
    assert store.get("missing") is None


def test_fetch_keeps_an_excerpt_and_the_full_page_in_the_store():
    store = InMemoryArtifactStore()
    toolkit = ArtifactToolkit(HugeToolkit(), store, excerpt_chars=100)

    page = toolkit.fetch(PAGE.url, CountryCode.UK)

    assert page.artifact_id
    assert page.text == "x" * 100
    assert store.get(page.artifact_id) == HUGE
    assert toolkit.hydrate(page).text == HUGE
