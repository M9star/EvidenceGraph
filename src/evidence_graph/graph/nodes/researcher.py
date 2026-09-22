from collections.abc import Callable, Mapping

from evidence_graph.state import (
    CountryCode,
    CountryReport,
    IncentiveRecord,
    ReportStatus,
    ResearchTask,
)
from evidence_graph.tools import ResearchToolkit
from evidence_graph.use_cases.ev_incentives import CountryProfile


def make_researcher(
    toolkit: ResearchToolkit,
    profiles: Mapping[CountryCode, CountryProfile],
    max_pages: int,
) -> Callable[[ResearchTask], dict]:
    def research_country(task: ResearchTask) -> dict:
        country = task["country"]
        profile = profiles[country]
        try:
            hits = toolkit.search(f"{task['query']} {profile.search_hint}", country)[:max_pages]
            incentives: list[IncentiveRecord] = []
            for hit in hits:
                page = toolkit.fetch(hit.url, country)
                incentives.extend(toolkit.extract(page, country))
        # A failed country must degrade to insufficient_evidence, never fail the whole run.
        except Exception as exc:
            report = CountryReport(
                country=country,
                status=ReportStatus.INSUFFICIENT_EVIDENCE,
                error=f"{type(exc).__name__}: {exc}",
            )
            return {"reports": [report]}

        status = ReportStatus.OK if incentives else ReportStatus.INSUFFICIENT_EVIDENCE
        report = CountryReport(country=country, status=status, incentives=incentives)
        return {"reports": [report]}

    return research_country
