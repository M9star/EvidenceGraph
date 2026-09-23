import json
from pathlib import Path

from pydantic import BaseModel, Field

from evidence_graph.state.models import CountryCode, IncentiveRecord
from evidence_graph.tools.base import FetchedPage, ResearchToolkit, SearchHit, ToolUnavailableError


class Recording(BaseModel):
    """Everything one country's researcher saw in a live run, so tests can replay it offline."""

    country: CountryCode
    hits: list[SearchHit] = Field(default_factory=list)
    pages: list[FetchedPage] = Field(default_factory=list)
    # Page URL -> one entry per extraction attempt, so replay also reproduces the retry path.
    extractions: dict[str, list[list[IncentiveRecord]]] = Field(default_factory=dict)


def recording_path(directory: Path, country: CountryCode) -> Path:
    return directory / f"{country.value.lower()}.json"


def load_recording(directory: Path, country: CountryCode) -> Recording:
    path = recording_path(directory, country)
    if not path.exists():
        return Recording(country=country)
    return Recording.model_validate_json(path.read_text(encoding="utf-8"))


def save_recording(directory: Path, recording: Recording) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    data = recording.model_dump(mode="json")
    path = recording_path(directory, recording.country)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class RecordingToolkit:
    """Passes calls to a live toolkit and writes every result to a per-country JSON file."""

    def __init__(self, inner: ResearchToolkit, directory: Path) -> None:
        self._inner = inner
        self._directory = directory

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        hits = self._inner.search(query, country)
        recording = Recording(country=country, hits=hits)
        save_recording(self._directory, recording)
        return hits

    def fetch(self, url: str, country: CountryCode) -> FetchedPage:
        page = self._inner.fetch(url, country)
        recording = load_recording(self._directory, country)
        recording.pages = [p for p in recording.pages if p.url != page.url] + [page]
        if page.url != url:
            recording.hits = [
                SearchHit(url=page.url, title=h.title) if h.url == url else h
                for h in recording.hits
            ]
        save_recording(self._directory, recording)
        return page

    def extract(
        self, page: FetchedPage, country: CountryCode, feedback: str | None = None
    ) -> list[IncentiveRecord]:
        records = self._inner.extract(page, country, feedback)
        recording = load_recording(self._directory, country)
        attempts = [] if feedback is None else recording.extractions.get(page.url, [])
        recording.extractions[page.url] = [*attempts, records]
        save_recording(self._directory, recording)
        return records


class ReplayToolkit:
    """Serves recorded search hits, pages, and extractions. Never touches the network."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def search(self, query: str, country: CountryCode) -> list[SearchHit]:
        return load_recording(self._directory, country).hits

    def fetch(self, url: str, country: CountryCode) -> FetchedPage:
        for page in load_recording(self._directory, country).pages:
            if page.url == url:
                return page
        raise ToolUnavailableError(f"no recorded page for {url}")

    def extract(
        self, page: FetchedPage, country: CountryCode, feedback: str | None = None
    ) -> list[IncentiveRecord]:
        attempts = load_recording(self._directory, country).extractions.get(page.url, [])
        if not attempts:
            return []
        return attempts[0] if feedback is None else attempts[-1]
