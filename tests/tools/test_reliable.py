from datetime import UTC, datetime

import pytest

from evidence_graph.graph.policies import ReliabilityPolicy
from evidence_graph.state import CountryCode
from evidence_graph.tools import (
    BudgetExceeded,
    FetchedPage,
    ReliableToolkit,
    SearchHit,
    ToolPolicyError,
    ToolUnavailableError,
    fingerprint_url,
)

UK = CountryCode.UK
PAGE = FetchedPage(
    url="https://www.gov.uk/electric-car-grant",
    title="Grant",
    text="The grant is £3,750.",
    retrieved_at=datetime(2026, 9, 24, tzinfo=UTC),
)


class ScriptedToolkit:
    def __init__(self) -> None:
        self.searches = 0
        self.fetches = 0
        self.fails_left = 0
        self.policy_error = False
        self.sleeps = 0.0

    def search(self, query, country):
        self.searches += 1
        self._maybe_fail()
        return [SearchHit(url=PAGE.url, title=PAGE.title)]

    def fetch(self, url, country):
        self.fetches += 1
        self._maybe_fail()
        return PAGE

    def extract(self, page, country, feedback=None):
        return []

    def _maybe_fail(self) -> None:
        if self.policy_error:
            raise ToolPolicyError("not allowed")
        if self.fails_left:
            self.fails_left -= 1
            raise ToolUnavailableError("blip")
        if self.sleeps:
            import time

            time.sleep(self.sleeps)


def _wrap(inner, **kwargs) -> ReliableToolkit:
    return ReliableToolkit(inner, ReliabilityPolicy(**kwargs))


def test_fingerprint_ignores_fragment_and_trailing_slash():
    assert fingerprint_url("https://GOV.UK/path/#x") == fingerprint_url("https://gov.uk/path")


def test_retries_transient_errors_then_succeeds():
    inner = ScriptedToolkit()
    inner.fails_left = 2
    toolkit = _wrap(inner, max_retries=2, retry_backoff_s=0)

    assert toolkit.search("q", UK)
    assert inner.searches == 3


def test_policy_errors_are_not_retried():
    inner = ScriptedToolkit()
    inner.policy_error = True
    toolkit = _wrap(inner, max_retries=2, retry_backoff_s=0)

    with pytest.raises(ToolPolicyError):
        toolkit.search("q", UK)
    assert inner.searches == 1


def test_duplicate_fetch_is_a_cache_hit():
    inner = ScriptedToolkit()
    toolkit = _wrap(inner)

    first = toolkit.fetch(PAGE.url, UK)
    second = toolkit.fetch(PAGE.url + "/", UK)

    assert first is second
    assert inner.fetches == 1


def test_budget_stops_further_calls():
    inner = ScriptedToolkit()
    toolkit = _wrap(inner, max_tool_calls=1)

    toolkit.search("q", UK)
    with pytest.raises(BudgetExceeded):
        toolkit.fetch(PAGE.url, UK)
    assert inner.fetches == 0


def test_slow_tool_is_marked_timed_out():
    inner = ScriptedToolkit()
    inner.sleeps = 0.04
    toolkit = _wrap(inner, tool_timeout_s=0.01, max_retries=0)

    with pytest.raises(ToolUnavailableError, match="timed out"):
        toolkit.search("q", UK)
