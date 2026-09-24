from evidence_graph.memory.summarizer import split_history
from evidence_graph.state import Comparison, ReportStatus, ResearchState, ResetHistory


def make_compare(history_keep_recent: int = 2):
    def compare(state: ResearchState) -> dict:
        by_country = {report.country: report for report in state.get("reports", [])}
        ordered = [by_country[code] for code in state["countries"] if code in by_country]
        missing = [
            code
            for code in state["countries"]
            if code not in by_country or by_country[code].status is not ReportStatus.OK
        ]
        comparison = Comparison(query=state["query"], reports=ordered, missing=missing)
        update: dict = {"comparison": comparison}
        history = list(state.get("history") or [])
        previous = state.get("comparison")
        if previous is not None:
            history.append(previous)
        summaries, recent = split_history(history, history_keep_recent)
        if previous is not None or summaries:
            update["history"] = ResetHistory(recent)
        if summaries:
            update["history_summaries"] = summaries
        return update

    return compare
