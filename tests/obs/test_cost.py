from uuid import uuid4

from evidence_graph.graph import invoke_comparison
from evidence_graph.obs import CostLedger, CostRates, UsageEvent
from evidence_graph.state import CountryCode


def test_ledger_charges_search_and_keeps_tokens():
    ledger = CostLedger(CostRates(search_usd=0.01, prompt_token_usd=0.001))
    run = ledger.start(user_id="a", thread_id="t", run_id="r1")
    ledger.record(
        UsageEvent(kind="search", name="search", country="UK", latency_s=0.1),
        run_id=run.run_id,
    )
    ledger.record(
        UsageEvent(
            kind="extract",
            name="extract",
            country="UK",
            latency_s=0.2,
            prompt_tokens=10,
            completion_tokens=5,
        ),
        run_id=run.run_id,
    )
    finished = ledger.finish(run.run_id, latency_s=1.5)

    assert finished is not None
    assert finished.tool_calls == 2
    assert finished.tokens == 15
    assert finished.estimated_usd(ledger.rates) == 0.02
    assert finished.summary(ledger.rates)["run_id"] == "r1"


def test_fixture_run_records_three_tool_calls_per_country(graph, settings, query):
    run_id = str(uuid4())
    comparison, ledger = invoke_comparison(
        graph,
        settings,
        query,
        [CountryCode.UK, CountryCode.FR],
        "t-cost",
        run_id=run_id,
    )
    cost = ledger.get(run_id)

    assert comparison.reports
    assert cost is not None
    assert cost.tool_calls == 6
    assert cost.estimated_usd(ledger.rates) > 0
    assert cost.latency_s >= 0
