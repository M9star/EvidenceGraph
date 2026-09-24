from evidence_graph.artifacts import ArtifactStore
from evidence_graph.state.models import CountryCode, IncentiveRecord
from evidence_graph.tools.base import FetchedPage, ResearchToolkit, SearchHit


class ArtifactToolkit:
    """Stores the full page by hash. Callers see an excerpt so state stays small."""

    def __init__(self, inner: ResearchToolkit, store: ArtifactStore, excerpt_chars: int) -> None:
        self._inner = inner
        self._store = store
        self._excerpt_chars = excerpt_chars

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        return self._inner.search(query, country)

    def fetch(self, url: str, country: CountryCode) -> FetchedPage:
        page = self._inner.fetch(url, country)
        digest = self._store.put(page.text)
        excerpt = page.text[: self._excerpt_chars]
        return page.model_copy(update={"text": excerpt, "artifact_id": digest})

    def extract(
        self, page: FetchedPage, country: CountryCode, feedback: str | None = None
    ) -> list[IncentiveRecord]:
        return self._inner.extract(self.hydrate(page), country, feedback)

    def hydrate(self, page: FetchedPage) -> FetchedPage:
        if not page.artifact_id:
            return page
        full = self._store.get(page.artifact_id)
        if full is None:
            return page
        return page.model_copy(update={"text": full})
