from collections.abc import Callable, Mapping

from langgraph.types import RunnableConfig

from evidence_graph.graph.nodes.quality_gate import extract_with_gate
from evidence_graph.memory.reports import ReportCache
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
    report_cache: ReportCache | None = None,
) -> Callable[[ResearchTask], dict]:
    def research_country(task: ResearchTask, config: RunnableConfig) -> dict:
        configurable = (config or {}).get("configurable", {})
        setter = getattr(toolkit, "set_run_deadline", None)
        if setter is not None:
            setter(configurable.get("run_deadline"))
        bind_run = getattr(toolkit, "set_run_id", None)
        if bind_run is not None:
            bind_run(configurable.get("run_id"))
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
            return {
                "reports": [
                    _with_fallback(
                        CountryReport(
                            country=country,
                            status=ReportStatus.INSUFFICIENT_EVIDENCE,
                            error=f"{type(exc).__name__}: {exc}",
                            warnings=warnings,
                        ),
                        report_cache,
                    )
                ]
            }

        status = ReportStatus.OK if incentives else ReportStatus.INSUFFICIENT_EVIDENCE
        report = CountryReport(
            country=country, status=status, incentives=incentives, warnings=warnings
        )
        return {"reports": [_with_fallback(report, report_cache)]}

    return research_country


def _with_fallback(report: CountryReport, cache: ReportCache | None) -> CountryReport:
    if cache is None:
        return report
    if report.status is ReportStatus.OK:
        cache.put(report)
        return report
    cached = cache.get(report.country)
    if cached is None or cached.status is not ReportStatus.OK:
        return report
    when = _retrieved_on(cached)
    warning = f"fallback: last-good {report.country.value} report from {when}"
    return cached.model_copy(update={"warnings": [*cached.warnings, warning, *report.warnings]})


def _retrieved_on(report: CountryReport) -> str:
    times = [
        citation.retrieved_at for incentive in report.incentives for citation in incentive.citations
    ]
    if not times:
        return "unknown"
    return max(times).date().isoformat()
