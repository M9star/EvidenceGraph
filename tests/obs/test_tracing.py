from evidence_graph.graph import run_comparison
from evidence_graph.obs import configure_tracing, memory_exporter
from evidence_graph.state import CountryCode


def test_a_run_emits_graph_node_and_tool_spans(graph, settings, query):
    configure_tracing(settings)
    exporter = memory_exporter()
    exporter.clear()

    run_comparison(graph, settings, query, [CountryCode.UK], thread_id="t-trace")

    names = {span.name for span in exporter.get_finished_spans()}
    assert {
        "graph.run",
        "node.planner",
        "node.researcher",
        "node.comparator",
        "tool.search",
        "tool.fetch",
        "tool.extract",
    } <= names


def test_researcher_span_records_the_country(graph, settings, query):
    configure_tracing(settings)
    exporter = memory_exporter()
    exporter.clear()

    run_comparison(graph, settings, query, [CountryCode.FR], thread_id="t-span-fr")

    researcher = next(
        item for item in exporter.get_finished_spans() if item.name == "node.researcher"
    )
    assert researcher.attributes["country"] == "FR"
