from evidence_graph.state import Comparison


def summarize_comparison(comparison: Comparison) -> str:
    """One line the graph can keep instead of a full older turn."""
    parts = [
        f"{report.country.value} {report.status.value} ({len(report.incentives)} incentives)"
        for report in comparison.reports
    ]
    missing = ",".join(code.value for code in comparison.missing) or "none"
    query = comparison.query if len(comparison.query) <= 80 else comparison.query[:77] + "..."
    return f"{query} | {'; '.join(parts)} | missing={missing}"


def split_history(
    history: list[Comparison], keep_recent: int
) -> tuple[list[str], list[Comparison]]:
    """Older turns become summaries; the last `keep_recent` stay raw."""
    if keep_recent < 1 or len(history) <= keep_recent:
        return [], history
    older, recent = history[:-keep_recent], history[-keep_recent:]
    return [summarize_comparison(item) for item in older], recent
