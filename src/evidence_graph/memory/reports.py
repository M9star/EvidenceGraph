from threading import Lock
from typing import Protocol

from evidence_graph.state import CountryCode, CountryReport, ReportStatus


class ReportCache(Protocol):
    def get(self, country: CountryCode) -> CountryReport | None: ...
    def put(self, report: CountryReport) -> None: ...


class InMemoryReportCache:
    """Last-good CountryReport per country. Stale-but-dated beats nothing."""

    def __init__(self) -> None:
        self._reports: dict[CountryCode, CountryReport] = {}
        self._lock = Lock()

    def get(self, country: CountryCode) -> CountryReport | None:
        with self._lock:
            return self._reports.get(country)

    def put(self, report: CountryReport) -> None:
        if report.status is not ReportStatus.OK:
            return
        with self._lock:
            self._reports[report.country] = report
