from collections.abc import Callable, Mapping

from evidence_graph.graph.nodes.quality_gate import extract_with_gate
from evidence_graph.state import (
    CountryCode,
    CountryReport,
    IncentiveRecord,
    ReportStatus,
    ResearchTask,
)
from evidence_graph.tools import ResearchToolkit, ToolError
from evidence_graph.use_cases.ev_incentives import CountryProfile


def make_researcher(
    toolkit: ResearchToolkit,
    profiles: Mapping[CountryCode, CountryProfile],
    max_pages: int,
    max_attempts: int = 2,
) -> Callable[[ResearchTask], dict]:
    def research_country(task: ResearchTask) -> dict:
        country = task["country"]
        profile = profiles[country]
        incentives: list[IncentiveRecord] = []
        warnings: list[str] = []
        try:
            hits = toolkit.search(f"{task['query']} {profile.search_hint}", country)[:max_pages]
            for hit in hits:
                # One bad page must not discard evidence already gathered from the others.
                try:
                    page = toolkit.fetch(hit.url, country)
                    result = extract_with_gate(toolkit, page, country, max_attempts)
                except ToolError as exc:
                    warnings.append(f"{hit.url}: {type(exc).__name__}: {exc}")
                    continue
                incentives.extend(result.accepted)
                warnings.extend(result.problems)
        # A failed country must degrade to insufficient_evidence, never fail the whole run.
        except Exception as exc:
            report = CountryReport(
                country=country,
                status=ReportStatus.INSUFFICIENT_EVIDENCE,
                error=f"{type(exc).__name__}: {exc}",
                warnings=warnings,
            )
            return {"reports": [report]}

        status = ReportStatus.OK if incentives else ReportStatus.INSUFFICIENT_EVIDENCE
        report = CountryReport(
            country=country, status=status, incentives=incentives, warnings=warnings
        )
        return {"reports": [report]}

    return research_country
