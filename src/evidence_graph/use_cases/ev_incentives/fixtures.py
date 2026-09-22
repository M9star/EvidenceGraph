from datetime import UTC, datetime

from evidence_graph.state.models import CountryCode
from evidence_graph.tools.base import FetchedPage

_RETRIEVED_AT = datetime(2026, 1, 1, tzinfo=UTC)

FIXTURE_PAGES: dict[CountryCode, list[FetchedPage]] = {
    CountryCode.FR: [
        FetchedPage(
            url="https://www.service-public.fr/",
            title="Fixture: France EV incentives",
            text="Fixture page. Not real policy data.",
            retrieved_at=_RETRIEVED_AT,
        )
    ],
    CountryCode.DE: [
        FetchedPage(
            url="https://www.bafa.de/",
            title="Fixture: Germany EV incentives",
            text="Fixture page. Not real policy data.",
            retrieved_at=_RETRIEVED_AT,
        )
    ],
    CountryCode.UK: [
        FetchedPage(
            url="https://www.gov.uk/",
            title="Fixture: UK EV incentives",
            text="Fixture page. Not real policy data.",
            retrieved_at=_RETRIEVED_AT,
        )
    ],
    CountryCode.IN: [
        FetchedPage(
            url="https://heavyindustries.gov.in/",
            title="Fixture: India EV incentives",
            text="Fixture page. Not real policy data.",
            retrieved_at=_RETRIEVED_AT,
        )
    ],
}
